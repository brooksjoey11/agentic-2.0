"""
Idempotency Middleware
Ensures that requests with the same idempotency key return the same result.
"""

import hashlib
import json
import logging
from typing import Optional, Callable, Awaitable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..cache.redis import get_redis_client
from ..config import config

logger = logging.getLogger(__name__)


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Middleware that handles idempotency keys for POST/PUT/PATCH requests.
    
    Behavior:
    1. Extract idempotency key from header 'Idempotency-Key'
    2. If key exists and request already processed, return cached response
    3. If key exists but request not processed, process and cache result
    4. If no key, process normally (no idempotency guarantee)
    
    Cache TTL: 24 hours (configurable)
    """
    
    def __init__(
        self,
        app: ASGIApp,
        ttl_seconds: int = 86400,  # 24 hours
        methods: list = ["POST", "PUT", "PATCH", "DELETE"],
        max_response_size: int = 1024 * 1024  # 1 MB
    ):
        super().__init__(app)
        self.ttl_seconds = ttl_seconds
        self.max_response_size = max_response_size
        self.methods = methods
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Only apply to configured methods
        if request.method not in self.methods:
            return await call_next(request)
        
        # Extract idempotency key
        idempotency_key = request.headers.get("Idempotency-Key")
        
        # If no key, process normally
        if not idempotency_key:
            return await call_next(request)
        
        # Validate key format
        if len(idempotency_key) < 8 or len(idempotency_key) > 255:
            raise HTTPException(
                status_code=400,
                detail="Idempotency-Key must be between 8 and 255 characters"
            )
        
        # Generate cache key
        cache_key = self._generate_cache_key(request, idempotency_key)
        
        # Check Redis for cached response
        redis = await get_redis_client()
        cached = await redis.get(cache_key)
        
        if cached:
            # Return cached response
            logger.debug(f"Idempotency hit for key: {idempotency_key}")
            cached_data = json.loads(cached)
            return self._reconstruct_response(cached_data)
        
        # Process request normally
        response = await call_next(request)
        
        # Only cache successful responses (2xx)
        if 200 <= response.status_code < 300:
            # Cache the response
            await self._cache_response(redis, cache_key, response)
            logger.debug(f"Cached response for key: {idempotency_key}")
        
        return response
    
    def _generate_cache_key(self, request: Request, idempotency_key: str) -> str:
        """Generate unique cache key from request and idempotency key."""
        # Include path and method to avoid collisions across endpoints
        base = f"{request.method}:{request.url.path}:{idempotency_key}"
        return f"idempotency:{hashlib.sha256(base.encode()).hexdigest()}"
    
    async def _cache_response(self, redis, cache_key: str, response: Response):
        """Cache response for future idempotent requests."""
        # Extract response data
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
            if len(body) > self.max_response_size:
                # Response too large to cache; reconstruct and return without caching
                response.body_iterator = self._iterate_body(body)
                return
        
        # Reconstruct body iterator for original response
        response.body_iterator = self._iterate_body(body)
        
        # Prepare cache data
        cache_data = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": body.decode('utf-8', errors='replace'),
            "media_type": response.media_type
        }
        
        # Store in Redis with TTL
        await redis.setex(
            cache_key,
            self.ttl_seconds,
            json.dumps(cache_data)
        )
    
    async def _iterate_body(self, body: bytes):
        """Helper to iterate over cached body."""
        yield body
    
    def _reconstruct_response(self, cached_data: dict) -> Response:
        """Reconstruct Response object from cached data."""
        return Response(
            content=cached_data["body"],
            status_code=cached_data["status_code"],
            headers=cached_data["headers"],
            media_type=cached_data["media_type"]
        )
