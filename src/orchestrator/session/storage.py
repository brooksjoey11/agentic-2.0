"""
Redis Session Storage
Persists session state in Redis for stateless orchestrator.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from ..cache.redis import get_redis_client
from ..models.session import Session, Message

logger = logging.getLogger(__name__)


class SessionStorage:
    """
    Redis-backed session storage.
    
    Enables stateless orchestrator instances by storing session data in Redis.
    All session operations go through this class.
    """
    
    def __init__(self, redis_ttl: int = 86400):  # 24 hours default
        self.redis_ttl = redis_ttl
        self.redis = None
    
    async def _get_redis(self):
        """Lazy initialize Redis connection."""
        if not self.redis:
            self.redis = await get_redis_client()
        return self.redis
    
    def _session_key(self, session_id: str) -> str:
        """Redis key for session metadata."""
        return f"session:{session_id}:metadata"
    
    def _messages_key(self, session_id: str) -> str:
        """Redis key for session messages."""
        return f"session:{session_id}:messages"
    
    def _last_active_key(self, session_id: str) -> str:
        """Redis key for last active timestamp."""
        return f"session:{session_id}:last_active"
    
    async def save_session(self, session: Session):
        """Save session metadata to Redis."""
        redis = await self._get_redis()
        
        key = self._session_key(session.id)
        await redis.setex(
            key,
            self.redis_ttl,
            session.json()
        )
        
        logger.debug(f"Saved session {session.id} to Redis")
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session metadata from Redis."""
        redis = await self._get_redis()
        
        key = self._session_key(session_id)
        data = await redis.get(key)
        
        if data:
            return Session.parse_raw(data)
        return None
    
    async def delete_session(self, session_id: str):
        """Delete all session data from Redis."""
        redis = await self._get_redis()
        
        await redis.delete(
            self._session_key(session_id),
            self._messages_key(session_id),
            self._last_active_key(session_id)
        )
        
        logger.info(f"Deleted session {session_id} from Redis")
    
    async def add_message(self, session_id: str, message: Message):
        """Add message to session history."""
        redis = await self._get_redis()
        
        # Add to list
        key = self._messages_key(session_id)
        await redis.lpush(key, message.json())
        
        # Keep only last 100 messages
        await redis.ltrim(key, 0, 99)
        
        # Update last active
        await redis.set(
            self._last_active_key(session_id),
            datetime.now().isoformat()
        )
        
        logger.debug(f"Added message to session {session_id}")
    
    async def get_messages(self, session_id: str, limit: int = 50) -> List[Message]:
        """Get recent messages from session."""
        redis = await self._get_redis()
        
        key = self._messages_key(session_id)
        messages = await redis.lrange(key, 0, limit - 1)
        
        return [Message.parse_raw(msg) for msg in messages]
    
    async def update_last_active(self, session_id: str):
        """Update last active timestamp."""
        redis = await self._get_redis()
        
        await redis.set(
            self._last_active_key(session_id),
            datetime.now().isoformat(),
            ex=self.redis_ttl
        )
    
    async def get_last_active(self, session_id: str) -> Optional[datetime]:
        """Get last active timestamp."""
        redis = await self._get_redis()
        
        data = await redis.get(self._last_active_key(session_id))
        if data:
            return datetime.fromisoformat(data)
        return None
    
    async def cleanup_expired(self):
        """Remove expired sessions (called by background task)."""
        # Redis automatically expires keys with TTL
        # This method exists for logging/metrics
        logger.info("Session cleanup completed (Redis auto-expiry)")
