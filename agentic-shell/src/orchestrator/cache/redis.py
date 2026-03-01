"""
Redis Cache Module
Redis connection and caching utilities
"""

import redis.asyncio as redis
from typing import Optional, Any
from functools import lru_cache

from ..config import config


class RedisClient:
    """Redis client wrapper"""
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
    
    async def initialize(self):
        """Initialize Redis connection"""
        self._client = await redis.from_url(
            config.redis.url,
            decode_responses=True,
            socket_keepalive=True,
            health_check_interval=30
        )
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        if not self._client:
            await self.initialize()
        return await self._client.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None):
        """Set key-value pair"""
        if not self._client:
            await self.initialize()
        await self._client.set(key, value, ex=ex)
    
    async def setex(self, key: str, seconds: int, value: str):
        """Set with expiration"""
        if not self._client:
            await self.initialize()
        await self._client.setex(key, seconds, value)
    
    async def delete(self, *keys: str):
        """Delete keys"""
        if not self._client:
            await self.initialize()
        await self._client.delete(*keys)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self._client:
            await self.initialize()
        return await self._client.exists(key) > 0
    
    async def expire(self, key: str, seconds: int):
        """Set expiration on key"""
        if not self._client:
            await self.initialize()
        await self._client.expire(key, seconds)
    
    async def ttl(self, key: str) -> int:
        """Get TTL of key"""
        if not self._client:
            await self.initialize()
        return await self._client.ttl(key)
    
    async def incr(self, key: str) -> int:
        """Increment counter"""
        if not self._client:
            await self.initialize()
        return await self._client.incr(key)
    
    async def decr(self, key: str) -> int:
        """Decrement counter"""
        if not self._client:
            await self.initialize()
        return await self._client.decr(key)
    
    async def lpush(self, key: str, *values: str):
        """Push to list head"""
        if not self._client:
            await self.initialize()
        await self._client.lpush(key, *values)
    
    async def rpush(self, key: str, *values: str):
        """Push to list tail"""
        if not self._client:
            await self.initialize()
        await self._client.rpush(key, *values)
    
    async def lpop(self, key: str) -> Optional[str]:
        """Pop from list head"""
        if not self._client:
            await self.initialize()
        return await self._client.lpop(key)
    
    async def rpop(self, key: str) -> Optional[str]:
        """Pop from list tail"""
        if not self._client:
            await self.initialize()
        return await self._client.rpop(key)
    
    async def lrange(self, key: str, start: int, stop: int):
        """Get list range"""
        if not self._client:
            await self.initialize()
        return await self._client.lrange(key, start, stop)
    
    async def ltrim(self, key: str, start: int, stop: int):
        """Trim list"""
        if not self._client:
            await self.initialize()
        await self._client.ltrim(key, start, stop)
    
    async def smembers(self, key: str):
        """Get set members"""
        if not self._client:
            await self.initialize()
        return await self._client.smembers(key)
    
    async def sadd(self, key: str, *members: str):
        """Add to set"""
        if not self._client:
            await self.initialize()
        await self._client.sadd(key, *members)
    
    async def srem(self, key: str, *members: str):
        """Remove from set"""
        if not self._client:
            await self.initialize()
        await self._client.srem(key, *members)
    
    async def ping(self) -> bool:
        """Ping Redis server"""
        if not self._client:
            await self.initialize()
        return await self._client.ping()
    
    async def flushall(self):
        """Flush all keys (use with caution)"""
        if not self._client:
            await self.initialize()
        await self._client.flushall()
    
    async def close(self):
        """Close Redis connection"""
        if self._client:
            await self._client.close()
            self._client = None


@lru_cache()
def get_redis_client() -> RedisClient:
    """Get Redis client singleton"""
    return RedisClient()