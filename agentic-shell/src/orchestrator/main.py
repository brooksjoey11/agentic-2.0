#!/usr/bin/env python3
"""
Agentic Shell 2.0 - Main Orchestrator
FastAPI application with WebSocket support for real-time agent communication
"""

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

import asyncpg
import redis.asyncio as redis
import aio_pika
import etcd3
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("orchestrator")

# =============================================================================
# Metrics
# =============================================================================
REQUEST_COUNT = Counter('orchestrator_requests_total', 'Total requests', ['endpoint', 'method'])
WEBSOCKET_CONNECTIONS = Gauge('orchestrator_websocket_connections', 'Active WebSocket connections')
RESPONSE_TIME = Histogram('orchestrator_response_time_seconds', 'Response time in seconds')
AGENT_TASKS = Counter('orchestrator_agent_tasks_total', 'Tasks routed to agents', ['agent_type'])
ERROR_COUNT = Counter('orchestrator_errors_total', 'Total errors', ['type'])

# =============================================================================
# Models
# =============================================================================

class MessageRole(str, Enum):
    USER = "user"
    SYSTEM = "system"
    AGENT = "agent"
    TOOL = "tool"

class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: MessageRole
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

class Session(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    agent_assignments: Dict[str, str] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    last_active: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

class AgentRequest(BaseModel):
    session_id: str
    message: Message
    agent_type: str

class AgentResponse(BaseModel):
    session_id: str
    message: Message
    agent_type: str
    processing_time: float

# =============================================================================
# Orchestrator Class
# =============================================================================

class Orchestrator:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.pg_pool: Optional[asyncpg.Pool] = None
        self.etcd: Optional[etcd3.Client] = None
        self.rabbit_channel: Optional[aio_pika.Channel] = None
        self.active_sessions: Dict[str, WebSocket] = {}
        
    async def initialize(self):
        """Initialize all connections"""
        try:
            # Redis
            self.redis = await redis.from_url(
                f"redis://{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', 6379)}",
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("✅ Connected to Redis")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise

        try:
            # PostgreSQL
            self.pg_pool = await asyncpg.create_pool(
                host=os.getenv('POSTGRES_HOST', 'postgres'),
                database=os.getenv('POSTGRES_DB', 'agentic'),
                user=os.getenv('POSTGRES_USER', 'agentic'),
                password=os.getenv('POSTGRES_PASSWORD', 'agentic123'),
                min_size=5,
                max_size=20
            )
            logger.info("✅ Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            raise

        try:
            # etcd
            self.etcd = etcd3.client(
                host=os.getenv('ETCD_HOST', 'etcd'),
                port=int(os.getenv('ETCD_PORT', 2379))
            )
            logger.info("✅ Connected to etcd")
        except Exception as e:
            logger.error(f"❌ etcd connection failed: {e}")
            raise

        try:
            # RabbitMQ
            connection = await aio_pika.connect_robust(
                f"amqp://{os.getenv('RABBITMQ_USER', 'agentic')}:{os.getenv('RABBITMQ_PASS', 'agentic123')}@"
                f"{os.getenv('RABBITMQ_HOST', 'rabbitmq')}:{os.getenv('RABBITMQ_PORT', 5672)}/"
            )
            self.rabbit_channel = await connection.channel()
            await self.rabbit_channel.declare_queue("agent.responses", durable=True)
            logger.info("✅ Connected to RabbitMQ")
        except Exception as e:
            logger.error(f"❌ RabbitMQ connection failed: {e}")
            raise

        # Start background tasks
        asyncio.create_task(self._process_responses())
        asyncio.create_task(self._cleanup_sessions())

    async def _process_responses(self):
        """Process responses from agents"""
        queue = await self.rabbit_channel.declare_queue("agent.responses", durable=True)
        
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        data = json.loads(message.body)
                        response = AgentResponse(**data)
                        
                        # Send to client via WebSocket
                        if response.session_id in self.active_sessions:
                            ws = self.active_sessions[response.session_id]
                            await ws.send_text(json.dumps(response.dict()))
                            
                        # Store in database
                        await self._store_message(response.message)
                        
                    except Exception as e:
                        logger.error(f"Error processing response: {e}")
                        ERROR_COUNT.labels(type='response_processing').inc()

    async def _cleanup_sessions(self):
        """Periodically clean up expired sessions"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                expired = []
                for session_id, ws in self.active_sessions.items():
                    # Check if session is expired
                    session_data = await self.redis.get(f"session:{session_id}:metadata")
                    if session_data:
                        session = Session(**json.loads(session_data))
                        if session.expires_at and session.expires_at < datetime.now():
                            expired.append(session_id)
                
                for session_id in expired:
                    await self.close_session(session_id)
                    logger.info(f"Cleaned up expired session: {session_id}")
                    
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")

    async def close_session(self, session_id: str):
        """Close a session and cleanup resources"""
        if session_id in self.active_sessions:
            ws = self.active_sessions[session_id]
            await ws.close()
            del self.active_sessions[session_id]
            WEBSOCKET_CONNECTIONS.dec()
            
        # Remove from Redis
        await self.redis.delete(f"session:{session_id}:metadata")
        await self.redis.delete(f"session:{session_id}:messages")

    async def _store_message(self, message: Message):
        """Store message in PostgreSQL"""
        async with self.pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO conversations (session_id, role, content, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                message.session_id,
                message.role.value,
                message.content,
                json.dumps(message.metadata),
                message.timestamp
            )

    async def route_message(self, message: Message) -> str:
        """Route message to appropriate agent based on intent"""
        RESPONSE_TIME.time()
        
        # Check etcd for agent assignment
        try:
            assignment = self.etcd.get(f"/sessions/{message.session_id}/agent")
            if assignment[0]:
                agent_type = assignment[0][0].decode()
                logger.debug(f"Using existing agent assignment: {agent_type}")
                return agent_type
        except Exception as e:
            logger.warning(f"etcd lookup failed: {e}")

        # Use planner to determine agent
        agent_type = await self._call_planner(message)
        
        # Store assignment in etcd
        try:
            self.etcd.put(f"/sessions/{message.session_id}/agent", agent_type)
        except Exception as e:
            logger.warning(f"etcd store failed: {e}")
        
        AGENT_TASKS.labels(agent_type=agent_type).inc()
        return agent_type

    async def _call_planner(self, message: Message) -> str:
        """Call planner agent to determine which specialist to use"""
        content = message.content.lower()
        
        # Simple keyword-based routing (in production, use actual agent)
        if any(word in content for word in ['write', 'code', 'function', 'script']):
            return 'coder'
        elif any(word in content for word in ['error', 'fix', 'broken', 'crash', 'bug']):
            return 'debugger'
        elif any(word in content for word in ['slow', 'performance', 'optimize', 'fast']):
            return 'optimizer'
        elif any(word in content for word in ['run', 'execute', 'deploy', 'kubectl', 'docker']):
            return 'executor'
        elif any(word in content for word in ['learn', 'remember', 'history']):
            return 'reflector'
        else:
            return 'planner'

    async def send_to_agent(self, request: AgentRequest):
        """Send message to appropriate agent via RabbitMQ"""
        await self.rabbit_channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(request.dict()).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=f"agent.{request.agent_type}"
        )

# =============================================================================
# FastAPI App
# =============================================================================

orchestrator = Orchestrator()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    await orchestrator.initialize()
    logger.info("🚀 Orchestrator started")
    yield
    # Cleanup
    if orchestrator.pg_pool:
        await orchestrator.pg_pool.close()
    logger.info("👋 Orchestrator shutdown")

app = FastAPI(
    title="Agentic Shell 2.0",
    description="Distributed Cognitive Architecture",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# REST Endpoints
# =============================================================================

@app.get("/")
async def root():
    REQUEST_COUNT.labels(endpoint='root', method='GET').inc()
    return {
        "name": "Agentic Shell 2.0",
        "version": "2.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health():
    REQUEST_COUNT.labels(endpoint='health', method='GET').inc()
    return {
        "status": "healthy",
        "redis": orchestrator.redis is not None,
        "postgres": orchestrator.pg_pool is not None,
        "etcd": orchestrator.etcd is not None,
        "rabbitmq": orchestrator.rabbit_channel is not None,
        "active_sessions": len(orchestrator.active_sessions)
    }

@app.get("/metrics")
async def metrics():
    REQUEST_COUNT.labels(endpoint='metrics', method='GET').inc()
    return Response(content=generate_latest(), media_type="text/plain")

@app.get("/stats")
async def get_stats():
    REQUEST_COUNT.labels(endpoint='stats', method='GET').inc()
    
    async with orchestrator.pg_pool.acquire() as conn:
        total_messages = await conn.fetchval("SELECT COUNT(*) FROM conversations")
        unique_sessions = await conn.fetchval("SELECT COUNT(DISTINCT session_id) FROM conversations")
        tool_executions = await conn.fetchval("SELECT COUNT(*) FROM tool_executions")
        
        # Get agent metrics
        agent_stats = await conn.fetch("""
            SELECT agent_type, 
                   COUNT(*) as executions,
                   AVG(duration_ms) as avg_duration
            FROM tool_executions 
            WHERE created_at > NOW() - INTERVAL '1 hour'
            GROUP BY agent_type
        """)
    
    return {
        "total_messages": total_messages,
        "unique_sessions": unique_sessions,
        "active_sessions": len(orchestrator.active_sessions),
        "tool_executions": tool_executions,
        "agent_stats": [dict(row) for row in agent_stats],
        "timestamp": datetime.now().isoformat()
    }

@app.post("/sessions/{session_id}")
async def create_session(session_id: str, user_id: Optional[str] = None):
    REQUEST_COUNT.labels(endpoint='create_session', method='POST').inc()
    
    session = Session(
        session_id=session_id,
        user_id=user_id,
        expires_at=datetime.now() + timedelta(days=7)
    )
    
    # Store in Redis
    await orchestrator.redis.set(
        f"session:{session_id}:metadata",
        json.dumps(session.dict(), default=str),
        ex=timedelta(days=7)
    )
    
    # Store in PostgreSQL
    async with orchestrator.pg_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO sessions (session_id, user_id, created_at, last_active, expires_at)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (session_id) DO UPDATE
            SET last_active = EXCLUDED.last_active,
                expires_at = EXCLUDED.expires_at
            """,
            session.session_id,
            session.user_id,
            session.created_at,
            session.last_active,
            session.expires_at
        )
    
    return {"status": "created", "session": session.dict()}

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    REQUEST_COUNT.labels(endpoint='delete_session', method='DELETE').inc()
    
    await orchestrator.close_session(session_id)
    
    return {"status": "closed", "session_id": session_id}

# =============================================================================
# WebSocket Endpoint
# =============================================================================

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    REQUEST_COUNT.labels(endpoint='websocket', method='CONNECT').inc()
    WEBSOCKET_CONNECTIONS.inc()
    
    await websocket.accept()
    orchestrator.active_sessions[session_id] = websocket
    logger.info(f"WebSocket connected: {session_id}")
    
    try:
        # Send welcome message
        await websocket.send_text(json.dumps({
            "type": "system",
            "content": f"Connected to Agentic Shell 2.0. Session: {session_id}",
            "timestamp": datetime.now().isoformat()
        }))
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Create message object
            message = Message(
                session_id=session_id,
                role=MessageRole(message_data.get('role', 'user')),
                content=message_data['content'],
                metadata=message_data.get('metadata', {})
            )
            
            # Store in Redis cache
            await orchestrator.redis.lpush(
                f"session:{session_id}:messages",
                json.dumps(message.dict(), default=str)
            )
            await orchestrator.redis.ltrim(f"session:{session_id}:messages", 0, 99)
            
            # Update session last active
            await orchestrator.redis.set(
                f"session:{session_id}:last_active",
                datetime.now().isoformat()
            )
            
            # Route to appropriate agent
            agent_type = await orchestrator.route_message(message)
            
            # Send to agent
            request = AgentRequest(
                session_id=session_id,
                message=message,
                agent_type=agent_type
            )
            await orchestrator.send_to_agent(request)
            
            # Store in PostgreSQL (async)
            asyncio.create_task(orchestrator._store_message(message))
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
        del orchestrator.active_sessions[session_id]
        WEBSOCKET_CONNECTIONS.dec()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ERROR_COUNT.labels(type='websocket').inc()
        if session_id in orchestrator.active_sessions:
            del orchestrator.active_sessions[session_id]
            WEBSOCKET_CONNECTIONS.dec()

# =============================================================================
# Main entry point
# =============================================================================

if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )