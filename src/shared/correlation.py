"""
Correlation ID Management
Ensures every request has a traceable ID across all services.
"""

import uuid
import logging
from contextvars import ContextVar
from typing import Optional

# Context variable for current correlation ID
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID from context."""
    return _correlation_id.get()


def set_correlation_id(correlation_id: str):
    """Set the current correlation ID in context."""
    _correlation_id.set(correlation_id)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


class CorrelationIdFilter(logging.Filter):
    """
    Logging filter that adds correlation ID to all log records.
    
    Usage:
        logger.addFilter(CorrelationIdFilter())
    """
    
    def filter(self, record):
        record.correlation_id = get_correlation_id() or "-"
        return True


class CorrelationIdMiddleware:
    """
    ASGI middleware that manages correlation IDs.
    
    - Extracts from request header or generates new
    - Sets in context for current request
    - Adds to response headers
    """
    
    def __init__(self, app, header_name: str = "X-Correlation-ID"):
        self.app = app
        self.header_name = header_name
        self._header_key = header_name.lower().encode()
        self._header_key_bytes = header_name.lower().encode()
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extract or generate correlation ID
        headers = dict(scope.get("headers", []))
        
        if self._header_key in headers:
            correlation_id = headers[self._header_key].decode()
        else:
            correlation_id = generate_correlation_id()
        
        # Set in context
        token = _correlation_id.set(correlation_id)
        
        # Wrap send to add header to response
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append(
                    (self._header_key, correlation_id.encode())
                )
                message["headers"] = headers
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Reset context
            _correlation_id.reset(token)
