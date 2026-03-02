"""
WebSocket Connection Manager
Manages WebSocket connections with Redis pub/sub for cross-instance communication.
"""

import asyncio
import json
import logging
from typing import Dict, Optional
from fastapi import WebSocket

from ..cache.redis import get_redis_client
from ..session.storage import SessionStorage

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections across multiple orchestrator instances.
    
    Uses Redis pub/sub to broadcast messages to all instances.
    Each instance maintains its own local connections but can send to any session.
    """
    
    def __init__(self):
        self.local_connections: Dict[str, WebSocket] = {}  # session_id -> websocket
        self.session_storage = SessionStorage()
        self.redis = None
        self.pubsub = None
        self._listener_task = None
    
    async def initialize(self):
        """Initialize Redis connections and start listener."""
        self.redis = await get_redis_client()
        self.pubsub = self.redis.pubsub()
        
        # Subscribe to broadcast channel
        await self.pubsub.subscribe("websocket:broadcast")
        
        # Start listener task
        self._listener_task = asyncio.create_task(self._listen_for_broadcasts())
        
        logger.info("Connection manager initialized")
    
    async def connect(self, session_id: str, websocket: WebSocket):
        """Register a new WebSocket connection."""
        await websocket.accept()
        self.local_connections[session_id] = websocket
        
        # Store in Redis for discovery
        await self.redis.sadd("active_websockets", session_id)
        
        logger.info(f"WebSocket connected: {session_id}")
    
    async def disconnect(self, session_id: str):
        """Remove a WebSocket connection."""
        if session_id in self.local_connections:
            del self.local_connections[session_id]
        
        # Remove from Redis
        await self.redis.srem("active_websockets", session_id)
        
        logger.info(f"WebSocket disconnected: {session_id}")
    
    async def send_to_session(self, session_id: str, message: dict):
        """
        Send message to a specific session.
        
        If the session is connected to this instance, send directly.
        Otherwise, broadcast to all instances.
        """
        # Check local first
        if session_id in self.local_connections:
            await self._send_local(session_id, message)
            return
        
        # Check if session exists anywhere
        exists = await self.redis.sismember("active_websockets", session_id)
        if exists:
            # Broadcast to all instances
            await self._broadcast(session_id, message)
        else:
            logger.warning(f"Session {session_id} not connected")
    
    async def _send_local(self, session_id: str, message: dict):
        """Send to locally connected session."""
        try:
            websocket = self.local_connections[session_id]
            await websocket.send_json(message)
            logger.debug(f"Sent message to local session {session_id}")
        except Exception as e:
            logger.error(f"Error sending to session {session_id}: {e}")
            await self.disconnect(session_id)
    
    async def _broadcast(self, session_id: str, message: dict):
        """Broadcast message to all orchestrator instances."""
        payload = {
            "type": "direct_message",
            "session_id": session_id,
            "message": message
        }
        
        await self.redis.publish(
            "websocket:broadcast",
            json.dumps(payload)
        )
        
        logger.debug(f"Broadcast message for session {session_id}")
    
    async def _listen_for_broadcasts(self):
        """Listen for broadcast messages from other instances.
        
        This loop runs indefinitely until the task is cancelled during shutdown().
        Do not await this directly; it is always run as an asyncio task.
        """
        async for message in self.pubsub.listen():
            if message["type"] != "message":
                continue
            
            try:
                data = json.loads(message["data"])
                
                if data["type"] == "direct_message":
                    session_id = data["session_id"]
                    
                    # If this session is local, send it
                    if session_id in self.local_connections:
                        await self._send_local(session_id, data["message"])
                        
            except Exception as e:
                logger.error(f"Error processing broadcast: {e}")
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast message to all connected sessions."""
        payload = {
            "type": "broadcast",
            "message": message
        }
        
        await self.redis.publish("websocket:broadcast", json.dumps(payload))
        
        # Also send to local connections
        for session_id in list(self.local_connections.keys()):
            await self._send_local(session_id, message)
    
    async def get_active_count(self) -> int:
        """Get number of active WebSocket connections."""
        global_count = await self.redis.scard("active_websockets")
        return global_count  # Return global count for metrics
    
    async def shutdown(self):
        """Gracefully shut down connection manager."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        
        # Close all local connections
        for session_id, websocket in list(self.local_connections.items()):
            try:
                await websocket.close()
            except Exception:
                pass
        
        if self.pubsub:
            await self.pubsub.unsubscribe("websocket:broadcast")
            await self.pubsub.close()
        
        logger.info("Connection manager shut down")
