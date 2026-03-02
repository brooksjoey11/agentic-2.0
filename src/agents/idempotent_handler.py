"""
Idempotent Message Handler for Agents
Prevents duplicate processing of the same message.
"""

import json
import hashlib
import logging
from typing import Optional, Dict, Any, Callable, Awaitable
from datetime import datetime, timedelta

from ..orchestrator.cache.redis import get_redis_client
from ..orchestrator.config import config

logger = logging.getLogger(__name__)


class IdempotentMessageHandler:
    """
    Wraps message processing with idempotency checks.
    
    Usage:
        handler = IdempotentMessageHandler()
        result = await handler.process(message, process_func)
    """
    
    def __init__(self, ttl_seconds: int = 86400):  # 24 hours
        self.ttl_seconds = ttl_seconds
        self.redis = None
    
    async def _get_redis(self):
        """Lazy initialize Redis connection."""
        if not self.redis:
            self.redis = await get_redis_client()
        return self.redis
    
    def _generate_message_id(self, message: Dict[str, Any]) -> str:
        """
        Generate unique ID for message based on content.
        
        Includes:
        - session_id
        - message content
        - timestamp (rounded to avoid exact duplicates)
        """
        content = f"{message.get('session_id', '')}:{message.get('content', '')}"
        # Round timestamp to nearest second to handle retries within same second
        timestamp = str(int(datetime.now().timestamp()))
        base = f"{content}:{timestamp}"
        
        return hashlib.sha256(base.encode()).hexdigest()
    
    async def is_processed(self, message_id: str) -> bool:
        """Check if message has already been processed."""
        redis = await self._get_redis()
        return await redis.exists(f"processed:{message_id}")
    
    async def mark_processed(self, message_id: str, result: Dict[str, Any]):
        """Mark message as processed and cache result."""
        redis = await self._get_redis()
        await redis.setex(
            f"processed:{message_id}",
            self.ttl_seconds,
            json.dumps(result)
        )
    
    async def get_cached_result(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get cached result for previously processed message."""
        redis = await self._get_redis()
        cached = await redis.get(f"processed:{message_id}")
        if cached:
            return json.loads(cached)
        return None
    
    async def process(
        self,
        message: Dict[str, Any],
        process_func: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]],
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process message with idempotency guarantee.
        
        Args:
            message: The message to process
            process_func: Async function that does the actual processing
            idempotency_key: Optional external idempotency key
        
        Returns:
            Processing result
        """
        # Use provided key or generate from message
        message_id = idempotency_key or self._generate_message_id(message)
        
        # Check if already processed
        if await self.is_processed(message_id):
            logger.info(f"Message {message_id} already processed, returning cached result")
            cached = await self.get_cached_result(message_id)
            if cached:
                return cached
        
        # Process the message
        try:
            result = await process_func(message)
            
            # Mark as processed
            await self.mark_processed(message_id, result)
            
            return result
            
        except Exception as e:
            # Don't mark as processed on failure (allow retry)
            logger.error(f"Message processing failed: {e}")
            raise
