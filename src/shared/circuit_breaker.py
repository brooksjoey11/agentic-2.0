"""
Circuit Breaker Pattern Implementation
Prevents cascading failures by failing fast when dependencies are down.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Optional, Callable, Any, Awaitable
from dataclasses import dataclass
from prometheus_client import Counter, Gauge

logger = logging.getLogger(__name__)

# Metrics
circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half-open)',
    ['name']
)

circuit_breaker_trips = Counter(
    'circuit_breaker_trips_total',
    'Circuit breaker trips',
    ['name']
)

circuit_breaker_requests = Counter(
    'circuit_breaker_requests_total',
    'Circuit breaker requests',
    ['name', 'result']  # success, failure, rejected
)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = 0      # Normal operation, requests allowed
    OPEN = 1        # Failing fast, requests rejected
    HALF_OPEN = 2   # Testing if service recovered


@dataclass
class CircuitConfig:
    """Configuration for circuit breaker."""
    
    # Number of failures to open circuit
    failure_threshold: int = 5
    
    # Time in seconds before attempting half-open
    timeout: int = 60
    
    # Number of test requests in half-open state
    test_request_count: int = 3
    
    # Success threshold in half-open to close circuit
    success_threshold: int = 2


class CircuitBreaker:
    """
    Circuit breaker implementation.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failing fast, requests rejected
    - HALF-OPEN: Testing recovery, limited requests allowed
    """
    
    def __init__(self, name: str, config: Optional[CircuitConfig] = None):
        self.name = name
        self.config = config or CircuitConfig()
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.test_requests_sent = 0
        self.test_successes = 0
        
        # Update metrics
        circuit_breaker_state.labels(name=self.name).set(self.state.value)
    
    async def call(
        self,
        func: Callable[..., Awaitable[Any]],
        fallback: Optional[Callable[..., Awaitable[Any]]] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Call a function with circuit breaker protection.
        
        Args:
            func: Async function to call
            fallback: Optional fallback function
            *args, **kwargs: Arguments to pass to func
        
        Returns:
            Function result or fallback result
        
        Raises:
            Exception: If circuit is open and no fallback
        """
        # Check if circuit is open
        if self.state == CircuitState.OPEN:
            if self._should_attempt_half_open():
                self._transition_to_half_open()
            else:
                circuit_breaker_requests.labels(
                    name=self.name, result="rejected"
                ).inc()
                
                if fallback:
                    return await fallback(*args, **kwargs)
                raise Exception(f"Circuit breaker {self.name} is OPEN")
        
        # In half-open state, only allow test requests
        if self.state == CircuitState.HALF_OPEN:
            if self.test_requests_sent >= self.config.test_request_count:
                circuit_breaker_requests.labels(
                    name=self.name, result="rejected"
                ).inc()
                
                if fallback:
                    return await fallback(*args, **kwargs)
                raise Exception(f"Circuit breaker {self.name} is HALF-OPEN (test limit reached)")
            
            self.test_requests_sent += 1
        
        # Attempt the call
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            circuit_breaker_requests.labels(name=self.name, result="success").inc()
            return result
            
        except Exception as e:
            self._record_failure()
            circuit_breaker_requests.labels(name=self.name, result="failure").inc()
            
            if fallback:
                return await fallback(*args, **kwargs)
            raise
    
    def _record_success(self):
        """Record a successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.test_successes += 1
            if self.test_successes >= self.config.success_threshold:
                self._transition_to_closed()
        
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def _record_failure(self):
        """Record a failed call."""
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.config.failure_threshold:
                self._transition_to_open()
        
        elif self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open trips back to open
            self._transition_to_open()
    
    def _should_attempt_half_open(self) -> bool:
        """Check if enough time has passed to try half-open."""
        return time.time() - self.last_failure_time >= self.config.timeout
    
    def _transition_to_open(self):
        """Transition from CLOSED/HALF-OPEN to OPEN."""
        self.state = CircuitState.OPEN
        self.failure_count = 0
        self.test_requests_sent = 0
        self.test_successes = 0
        
        circuit_breaker_trips.labels(name=self.name).inc()
        circuit_breaker_state.labels(name=self.name).set(self.state.value)
        
        logger.warning(f"Circuit breaker {self.name} opened")
    
    def _transition_to_half_open(self):
        """Transition from OPEN to HALF-OPEN."""
        self.state = CircuitState.HALF_OPEN
        self.test_requests_sent = 0
        self.test_successes = 0
        
        circuit_breaker_state.labels(name=self.name).set(self.state.value)
        
        logger.info(f"Circuit breaker {self.name} half-open (testing recovery)")
    
    def _transition_to_closed(self):
        """Transition from HALF-OPEN to CLOSED."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.test_requests_sent = 0
        self.test_successes = 0
        
        circuit_breaker_state.labels(name=self.name).set(self.state.value)
        
        logger.info(f"Circuit breaker {self.name} closed (recovered)")
    
    def get_state(self) -> dict:
        """Get current state for monitoring."""
        return {
            "name": self.name,
            "state": self.state.name,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "test_requests_sent": self.test_requests_sent,
            "test_successes": self.test_successes,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "timeout": self.config.timeout,
                "test_request_count": self.config.test_request_count,
                "success_threshold": self.config.success_threshold
            }
        }


# Registry of circuit breakers
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, config: Optional[CircuitConfig] = None) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]


def circuit_breaker(name: str, fallback: Optional[Callable] = None):
    """Decorator to apply circuit breaker to a function."""
    from functools import wraps
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cb = get_circuit_breaker(name)
            return await cb.call(func, fallback, *args, **kwargs)
        return wrapper
    return decorator
