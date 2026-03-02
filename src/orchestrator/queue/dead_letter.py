"""
Dead Letter Queue Handler
Manages messages that failed after max retries.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from ..db.pool import get_db_pool
from ..cache.redis import get_redis_client
from ..config import config

logger = logging.getLogger(__name__)


class DLQStatus(str, Enum):
    """Dead letter queue status."""
    FAILED = "failed"
    PENDING_RETRY = "pending_retry"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class DeadLetterQueue:
    """
    Dead Letter Queue for failed messages.
    
    Messages are moved here after exceeding max retries.
    Supports inspection, replay, and manual resolution.
    """
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.db = None
        self.redis = None
    
    async def _get_db(self):
        """Lazy initialize database connection."""
        if not self.db:
            self.db = await get_db_pool()
        return self.db
    
    async def _get_redis(self):
        """Lazy initialize Redis connection."""
        if not self.redis:
            self.redis = await get_redis_client()
        return self.redis
    
    async def move_to_dlq(
        self,
        original_message: Dict[str, Any],
        error: Exception,
        queue_name: str,
        retry_count: int
    ):
        """
        Move failed message to dead letter queue.
        
        Args:
            original_message: The message that failed
            error: The error that caused failure
            queue_name: Original queue name
            retry_count: Number of retry attempts
        """
        if retry_count < self.max_retries:
            # Not yet exceeded max retries
            return
        
        logger.warning(f"Message exceeded max retries ({self.max_retries}), moving to DLQ")
        
        # Prepare DLQ entry
        dlq_entry = {
            "original_message_id": original_message.get("id"),
            "queue_name": queue_name,
            "payload": original_message,
            "error": {
                "type": type(error).__name__,
                "message": str(error),
                "timestamp": datetime.now().isoformat()
            },
            "retry_count": retry_count,
            "status": DLQStatus.FAILED,
            "created_at": datetime.now().isoformat()
        }
        
        # Store in database
        db = await self._get_db()
        await db.execute("""
            INSERT INTO dead_letter_queue 
                (original_message_id, queue_name, payload, error, retry_count, status, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
            dlq_entry["original_message_id"],
            dlq_entry["queue_name"],
            json.dumps(dlq_entry["payload"]),
            json.dumps(dlq_entry["error"]),
            dlq_entry["retry_count"],
            dlq_entry["status"],
            datetime.fromisoformat(dlq_entry["created_at"])
        )
        
        # Also cache in Redis for fast access
        redis = await self._get_redis()
        await redis.lpush("dlq:recent", json.dumps(dlq_entry))
        await redis.ltrim("dlq:recent", 0, 99)
        
        # Increment metrics
        from ..metrics import dlq_messages
        dlq_messages.labels(queue=queue_name).inc()
    
    async def list_failed(
        self,
        status: Optional[DLQStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List messages in dead letter queue."""
        db = await self._get_db()
        
        if status:
            query = "SELECT * FROM dead_letter_queue WHERE status = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3"
            params = [status.value, limit, offset]
        else:
            query = "SELECT * FROM dead_letter_queue ORDER BY created_at DESC LIMIT $1 OFFSET $2"
            params = [limit, offset]
        
        rows = await db.fetch(query, *params)
        
        return [
            {
                "id": row["id"],
                "original_message_id": row["original_message_id"],
                "queue_name": row["queue_name"],
                "payload": row["payload"],
                "error": row["error"],
                "retry_count": row["retry_count"],
                "status": row["status"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat()
            }
            for row in rows
        ]
    
    async def retry_message(self, dlq_id: int) -> bool:
        """
        Retry a message from dead letter queue.
        
        Returns:
            True if message was queued for retry
        """
        db = await self._get_db()
        
        # Get the message
        row = await db.fetchrow(
            "SELECT * FROM dead_letter_queue WHERE id = $1",
            dlq_id
        )
        
        if not row:
            logger.error(f"DLQ message {dlq_id} not found")
            return False
        
        # Update status
        await db.execute(
            "UPDATE dead_letter_queue SET status = $1, updated_at = NOW() WHERE id = $2",
            DLQStatus.PENDING_RETRY.value,
            dlq_id
        )
        
        # Publish back to original queue (implementation depends on queue system)
        # This would call RabbitMQ to republish the message
        
        logger.info(f"Message {dlq_id} queued for retry")
        return True
    
    async def resolve_message(self, dlq_id: int, resolution: str):
        """Mark a DLQ message as resolved (manual intervention)."""
        db = await self._get_db()
        
        await db.execute(
            "UPDATE dead_letter_queue SET status = $1, updated_at = NOW() WHERE id = $2",
            DLQStatus.RESOLVED.value,
            dlq_id
        )
        
        logger.info(f"DLQ message {dlq_id} resolved: {resolution}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about dead letter queue."""
        db = await self._get_db()
        
        # Total count
        total = await db.fetchval("SELECT COUNT(*) FROM dead_letter_queue")
        
        # Count by status
        by_status = await db.fetch("""
            SELECT status, COUNT(*) as count
            FROM dead_letter_queue
            GROUP BY status
        """)
        
        # Count by queue
        by_queue = await db.fetch("""
            SELECT queue_name, COUNT(*) as count
            FROM dead_letter_queue
            GROUP BY queue_name
        """)
        
        # Recent errors (last hour)
        recent = await db.fetchval("""
            SELECT COUNT(*) FROM dead_letter_queue
            WHERE created_at > NOW() - INTERVAL '1 hour'
        """)
        
        return {
            "total_messages": total,
            "by_status": {row["status"]: row["count"] for row in by_status},
            "by_queue": {row["queue_name"]: row["count"] for row in by_queue},
            "recent_errors_last_hour": recent
        }
