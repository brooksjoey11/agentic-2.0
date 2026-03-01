"""
Session Service
Manages WebSocket sessions and conversation state
"""

import json
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from fastapi import WebSocket

from ..models.session import Session, SessionCreate, Message
from ..models.agent import AgentRequest
from ..db.database import DatabasePool
from ..cache.redis import RedisClient
from ..messaging.rabbitmq import RabbitMQChannel


class SessionService:
    """Service for managing sessions"""
    
    def __init__(self, db_pool: DatabasePool, redis: RedisClient, queue: RabbitMQChannel):
        self.db_pool = db_pool
        self.redis = redis
        self.queue = queue
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def create_session(self, session_data: SessionCreate) -> Session:
        """Create a new session"""
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        session = Session(
            id=session_id,
            user_id=session_data.user_id,
            metadata=session_data.metadata,
            created_at=now,
            last_active=now,
            expires_at=now + timedelta(days=session_data.ttl_days) if session_data.ttl_days else None
        )
        
        # Store in database
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO sessions (session_id, user_id, metadata, created_at, last_active, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, session.id, session.user_id, json.dumps(session.metadata),
                session.created_at, session.last_active, session.expires_at)
        
        # Cache in Redis
        await self.redis.setex(
            f"session:{session_id}:metadata",
            3600,  # 1 hour cache
            session.json()
        )
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        # Try Redis cache first
        cached = await self.redis.get(f"session:{session_id}:metadata")
        if cached:
            return Session.parse_raw(cached)
        
        # Fall back to database
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT session_id, user_id, metadata, created_at, last_active, expires_at
                FROM sessions WHERE session_id = $1
            """, session_id)
            
            if row:
                session = Session(
                    id=row['session_id'],
                    user_id=row['user_id'],
                    metadata=row['metadata'],
                    created_at=row['created_at'],
                    last_active=row['last_active'],
                    expires_at=row['expires_at']
                )
                
                # Cache for next time
                await self.redis.setex(
                    f"session:{session_id}:metadata",
                    3600,
                    session.json()
                )
                
                return session
        
        return None
    
    async def delete_session(self, session_id: str) -> None:
        """Delete a session"""
        # Remove from database
        async with self.db_pool.acquire() as conn:
            await conn.execute("DELETE FROM sessions WHERE session_id = $1", session_id)
        
        # Remove from cache
        await self.redis.delete(f"session:{session_id}:metadata")
        await self.redis.delete(f"session:{session_id}:messages")
        
        # Close WebSocket if active
        if session_id in self.active_connections:
            await self.active_connections[session_id].close()
            del self.active_connections[session_id]
    
    async def list_sessions(self, user_id: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Session]:
        """List sessions"""
        async with self.db_pool.acquire() as conn:
            if user_id:
                rows = await conn.fetch("""
                    SELECT session_id, user_id, metadata, created_at, last_active, expires_at
                    FROM sessions WHERE user_id = $1
                    ORDER BY last_active DESC
                    OFFSET $2 LIMIT $3
                """, user_id, skip, limit)
            else:
                rows = await conn.fetch("""
                    SELECT session_id, user_id, metadata, created_at, last_active, expires_at
                    FROM sessions
                    ORDER BY last_active DESC
                    OFFSET $1 LIMIT $2
                """, skip, limit)
            
            return [Session(
                id=row['session_id'],
                user_id=row['user_id'],
                metadata=row['metadata'],
                created_at=row['created_at'],
                last_active=row['last_active'],
                expires_at=row['expires_at']
            ) for row in rows]
    
    async def add_message(self, session_id: str, role: str, content: str, metadata: Dict[str, Any] = None) -> Message:
        """Add a message to session history"""
        message = Message(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata or {}
        )
        
        # Store in database
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO conversations (session_id, role, content, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5)
            """, session_id, role, content, json.dumps(metadata or {}), message.timestamp)
        
        # Cache in Redis (keep last 100 messages)
        await self.redis.lpush(
            f"session:{session_id}:messages",
            message.json()
        )
        await self.redis.ltrim(f"session:{session_id}:messages", 0, 99)
        
        # Update session last_active
        await self.redis.set(f"session:{session_id}:last_active", datetime.now().isoformat())
        
        return message
    
    async def get_messages(self, session_id: str, limit: int = 50) -> List[Message]:
        """Get session message history"""
        # Try Redis cache first
        cached = await self.redis.lrange(f"session:{session_id}:messages", 0, limit - 1)
        if cached:
            return [Message.parse_raw(msg) for msg in cached]
        
        # Fall back to database
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT role, content, metadata, created_at
                FROM conversations
                WHERE session_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """, session_id, limit)
            
            messages = []
            for row in reversed(rows):  # Return in chronological order
                messages.append(Message(
                    session_id=session_id,
                    role=row['role'],
                    content=row['content'],
                    metadata=row['metadata'],
                    timestamp=row['created_at']
                ))
            
            return messages
    
    async def register_connection(self, session_id: str, websocket: WebSocket) -> None:
        """Register WebSocket connection for session"""
        self.active_connections[session_id] = websocket
        
        # Update session last_active
        await self.redis.set(f"session:{session_id}:last_active", datetime.now().isoformat())
    
    async def unregister_connection(self, session_id: str) -> None:
        """Unregister WebSocket connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def process_message(self, session_id: str, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a message through the agent pipeline"""
        # Store user message
        await self.add_message(session_id, "user", content, metadata)
        
        # Determine agent type (simplified - would use planner in production)
        agent_type = self._determine_agent_type(content)
        
        # Create agent request
        request = AgentRequest(
            session_id=session_id,
            message={
                "content": content,
                "metadata": metadata or {}
            },
            agent_type=agent_type
        )
        
        # Send to agent queue
        await self.queue.publish(
            exchange="agent_exchange",
            routing_key=f"agent.{agent_type}",
            body=json.dumps(request.dict()).encode()
        )
        
        # For now, return placeholder (in production, would wait for async response)
        return {
            "type": "processing",
            "message": f"Message routed to {agent_type} agent",
            "session_id": session_id
        }
    
    def _determine_agent_type(self, content: str) -> str:
        """Simple agent type determination (would use ML in production)"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['write', 'code', 'function', 'script']):
            return 'coder'
        elif any(word in content_lower for word in ['error', 'fix', 'broken', 'crash', 'bug']):
            return 'debugger'
        elif any(word in content_lower for word in ['slow', 'performance', 'optimize', 'fast']):
            return 'optimizer'
        elif any(word in content_lower for word in ['run', 'execute', 'deploy', 'kubectl', 'docker']):
            return 'executor'
        elif any(word in content_lower for word in ['learn', 'remember', 'history']):
            return 'reflector'
        else:
            return 'planner'