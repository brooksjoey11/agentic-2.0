"""
Redis Sliding Window Rate Limiter
Enforces rate limits with sliding window algorithm.
"""

import time
import logging
from typing import Optional, Tuple, Dict
from dataclasses import dataclass

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..cache.redis import get_redis_client
from ..config import config

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    
    allowed: bool
    limit: int
    remaining: int
    reset_after: int  # seconds until reset
    retry_after: Optional[int] = None  # seconds to wait if blocked


class TieredRateLimiter:
    """
    Redis-based sliding window rate limiter with tiered limits.
    
    Supports:
    - Free tier: 5 requests per day
    - Pro tier: 100 requests per day
    - Enterprise: 1000 requests per day
    - Custom per-endpoint limits
    """
    
    def __init__(self):
        self.redis = None
        
        # Tier limits (requests per day)
        self.tier_limits = {
            "free": int(config.get("FREE_TIER_LIMIT", "5")),
            "pro": int(config.get("PRO_TIER_LIMIT", "100")),
            "enterprise": int(config.get("ENTERPRISE_TIER_LIMIT", "1000"))
        }
        
        # Window size in seconds (24 hours)
        self.window_seconds = 86400
        
        # Endpoint-specific overrides
        self.endpoint_overrides = {
            "/health": None,  # No limit
            "/metrics": None,  # No limit
        }
    
    async def _get_redis(self):
        """Lazy initialize Redis connection."""
        if not self.redis:
            self.redis = await get_redis_client()
        return self.redis
    
    def _get_user_tier(self, user_id: Optional[str]) -> str:
        """Determine user tier (would query database in production)."""
        # Placeholder - in production, would look up user from DB
        if not user_id:
            return "free"
        
        # For testing/demo, allow override via user_id prefix
        if user_id.startswith("pro_"):
            return "pro"
        elif user_id.startswith("enterprise_"):
            return "enterprise"
        
        return "free"
    
    def _get_key(self, identifier: str, endpoint: str) -> str:
        """Generate Redis key for rate limit counter."""
        return f"ratelimit:{identifier}:{endpoint}"
    
    async def check_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        user_id: Optional[str] = None,
        custom_limit: Optional[int] = None
    ) -> RateLimitResult:
        """
        Check if request is within rate limits.
        
        Args:
            identifier: Unique identifier (user ID, API key, IP)
            endpoint: API endpoint being accessed
            user_id: User ID for tier determination
            custom_limit: Override default limit
        
        Returns:
            RateLimitResult with allowed flag and headers info
        """
        # Check endpoint override
        if endpoint in self.endpoint_overrides:
            if self.endpoint_overrides[endpoint] is None:
                # No limit for this endpoint
                return RateLimitResult(
                    allowed=True,
                    limit=0,
                    remaining=0,
                    reset_after=0
                )
        
        redis = await self._get_redis()
        key = self._get_key(identifier, endpoint)
        now = int(time.time())
        window_start = now - self.window_seconds
        
        # Determine limit
        if custom_limit:
            limit = custom_limit
        else:
            tier = self._get_user_tier(user_id)
            limit = self.tier_limits.get(tier, self.tier_limits["free"])
        
        # Use Redis sorted set for sliding window
        # Each request is a member with score = timestamp
        
        # Remove old requests outside window
        await redis.zremrangebyscore(key, 0, window_start)
        
        # Count requests in current window
        current_count = await redis.zcard(key)
        
        # Calculate reset time (when oldest request expires)
        oldest = await redis.zrange(key, 0, 0, withscores=True)
        if oldest:
            oldest_timestamp = int(oldest[0][1])
            reset_after = max(0, self.window_seconds - (now - oldest_timestamp))
        else:
            reset_after = self.window_seconds
        
        # Check if over limit
        if current_count >= limit:
            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_after=reset_after,
                retry_after=reset_after
            )
        
        # Add current request
        await redis.zadd(key, {str(now): now})
        
        # Set expiry on the key (window + 1 hour)
        await redis.expire(key, self.window_seconds + 3600)
        
        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=limit - current_count - 1,
            reset_after=reset_after
        )
    
    async def get_usage_stats(self, identifier: str, endpoint: str) -> Dict:
        """Get current usage statistics for an identifier."""
        redis = await self._get_redis()
        key = self._get_key(identifier, endpoint)
        
        now = int(time.time())
        window_start = now - self.window_seconds
        
        # Clean up old entries
        await redis.zremrangebyscore(key, 0, window_start)
        
        # Get current count
        current_count = await redis.zcard(key)
        
        # Get oldest request for reset calculation
        oldest = await redis.zrange(key, 0, 0, withscores=True)
        if oldest:
            oldest_timestamp = int(oldest[0][1])
            reset_after = max(0, self.window_seconds - (now - oldest_timestamp))
        else:
            reset_after = self.window_seconds
        
        return {
            "current_count": current_count,
            "reset_after_seconds": reset_after,
            "window_seconds": self.window_seconds
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    
    Adds rate limit headers to responses:
    - X-RateLimit-Limit
    - X-RateLimit-Remaining
    - X-RateLimit-Reset
    """
    
    def __init__(
        self,
        app: ASGIApp,
        limiter: TieredRateLimiter,
        exclude_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.limiter = limiter
        self.exclude_paths = exclude_paths or []
    
    async def dispatch(self, request: Request, call_next):
        # Skip excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Get identifier (user ID, API key, or IP)
        user_id = getattr(request.state, "user_id", None)
        api_key = request.headers.get("X-API-Key")
        client_ip = request.client.host if request.client else None
        identifier = user_id or api_key or client_ip
        
        if not identifier:
            raise HTTPException(status_code=400, detail="Cannot identify request source for rate limiting")
        
        # Check rate limit
        result = await self.limiter.check_rate_limit(
            identifier=identifier,
            endpoint=request.url.path,
            user_id=user_id
        )
        
        if not result.allowed:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={
                    "Retry-After": str(result.retry_after),
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(result.reset_after)
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(result.reset_after)
        
        return response
