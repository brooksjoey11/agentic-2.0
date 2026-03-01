"""
Integration Tests for Agent Pipeline
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.orchestrator.main import Orchestrator
from src.orchestrator.models.session import SessionCreate, Message
from src.agents.worker import PlannerAgent, ExecutorAgent, CoderAgent
from src.tools.registry import tool_registry
from src.tools.shell import Tool as ShellTool


@pytest.mark.integration
class TestFullPipeline:
    """Test complete agent pipeline"""
    
    @pytest.fixture
    async def orchestrator(self):
        """Create orchestrator with mocked dependencies"""
        orch = Orchestrator()
        
        # Mock connections
        orch.redis = AsyncMock()
        orch.redis.get.return_value = None
        orch.redis.set.return_value = True
        orch.redis.lpush.return_value = 1
        orch.redis.ltrim.return_value = True
        
        # Mock database
        orch.pg_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {
            "session_id": "test-session",
            "user_id": "test-user",
            "metadata": {},
            "created_at": datetime.now(),
            "last_active": datetime.now(),
            "expires_at": None
        }
        orch.pg_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Mock etcd
        orch.etcd = Mock()
        orch.etcd.get.return_value = (None, None)
        orch.etcd.put.return_value = None
        
        # Mock RabbitMQ
        orch.rabbit_channel = AsyncMock()
        orch.rabbit_channel.default_exchange.publish.return_value = None
        
        return orch
    
    @pytest.fixture
    def planner(self):
        """Create planner agent with mocked Mistral"""
        agent = PlannerAgent()
        agent.redis = AsyncMock()
        agent.rabbit_channel = AsyncMock()
        agent.mistral = AsyncMock()
        agent.mistral.beta.conversations.start.return_value = Mock(
            outputs=[Mock(text='{"plan": ["step1", "step2"]}')]
        )
        return agent
    
    @pytest.fixture
    def executor(self):
        """Create executor agent with mocked tools"""
        agent = ExecutorAgent()
        agent.redis = AsyncMock()
        agent.rabbit_channel = AsyncMock()
        agent.mistral = AsyncMock()
        
        # Register shell tool
        tool_registry.register("shell", ShellTool)
        agent.tools = {"shell": ShellTool()}
        
        return agent
    
    @pytest.mark.asyncio
    async def test_session_creation(self, orchestrator):
        """Test session creation flow"""
        session_data = SessionCreate(
            user_id="test-user",
            metadata={"client": "test"},
            ttl_days=1
        )
        
        session = await orchestrator.create_session(session_data)
        
        assert session.id is not None
        assert session.user_id == "test-user"
        assert session.metadata == {"client": "test"}
        assert session.expires_at is not None
        
        # Verify Redis storage
        orchestrator.redis.setex.assert_called_once()
        
        # Verify PostgreSQL storage
        mock_conn = await orchestrator.pg_pool.acquire().__aenter__()
        mock_conn.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_message_routing(self, orchestrator):
        """Test message routing to appropriate agent"""
        message = Message(
            session_id="test-session",
            role="user",
            content="Write a Python function to calculate fibonacci"
        )
        
        # Mock planner response
        orchestrator._call_planner = AsyncMock(return_value="coder")
        
        agent_type = await orchestrator.route_message(message)
        
        assert agent_type == "coder"
        
        # Verify etcd storage
        orchestrator.etcd.put.assert_called_once_with(
            "/sessions/test-session/agent", "coder"
        )
    
    @pytest.mark.asyncio
    async def test_agent_request_publishing(self, orchestrator):
        """Test publishing request to agent queue"""
        from src.orchestrator.models.agent import AgentRequest
        
        message = Message(
            session_id="test-session",
            role="user",
            content="Test message"
        )
        
        request = AgentRequest(
            session_id="test-session",
            message=message,
            agent_type="planner"
        )
        
        await orchestrator.send_to_agent(request)
        
        # Verify RabbitMQ publish
        orchestrator.rabbit_channel.default_exchange.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_planner_agent_processing(self, planner):
        """Test planner agent processing"""
        data = {
            "session_id": "test-session",
            "message": {
                "content": "Deploy a web application"
            }
        }
        
        result = await planner.process(data)
        
        assert result["metadata"]["type"] == "plan"
        assert "plan" in result["content"].lower()
    
    @pytest.mark.asyncio
    async def test_executor_agent_tool_execution(self, executor):
        """Test executor agent tool execution"""
        # Mock shell tool execution
        with patch.object(executor.tools["shell"], 'execute') as mock_shell:
            mock_shell.return_value = {"stdout": "command output"}
            
            data = {
                "session_id": "test-session",
                "message": {
                    "content": 'TOOL:{"tool": "shell", "args": {"cmd": "echo test"}}'
                }
            }
            
            result = await executor.process(data)
            
            assert result["metadata"]["tool_execution"] == "shell"
            assert "command output" in result["content"]
            mock_shell.assert_called_once_with(cmd="echo test")
    
    @pytest.mark.asyncio
    async def test_complete_pipeline_flow(self, orchestrator, planner, executor):
        """Test complete flow from message to response"""
        # 1. Create session
        session_data = SessionCreate(user_id="test-user")
        session = await orchestrator.create_session(session_data)
        
        # 2. Create and route message
        message = Message(
            session_id=session.id,
            role="user",
            content="Run a shell command"
        )
        
        # Mock routing
        orchestrator._call_planner = AsyncMock(return_value="executor")
        agent_type = await orchestrator.route_message(message)
        
        assert agent_type == "executor"
        
        # 3. Send to agent
        from src.orchestrator.models.agent import AgentRequest
        request = AgentRequest(
            session_id=session.id,
            message=message,
            agent_type=agent_type
        )
        
        await orchestrator.send_to_agent(request)
        
        # 4. Process with executor
        agent_data = {
            "session_id": session.id,
            "message": {"content": message.content}
        }
        
        # Mock tool execution
        with patch.object(executor.tools["shell"], 'execute') as mock_shell:
            mock_shell.return_value = {"stdout": "command output"}
            
            result = await executor.process(agent_data)
            
            assert "command output" in result["content"]
            
            # 5. Publish response
            response = {
                "session_id": session.id,
                "message": {
                    "id": "msg-123",
                    "session_id": session.id,
                    "role": "agent",
                    "content": result["content"],
                    "metadata": result["metadata"],
                    "timestamp": datetime.now().isoformat()
                },
                "agent_type": "executor",
                "processing_time": 100
            }
            
            await executor.rabbit_channel.default_exchange.publish(
                AsyncMock(),
                routing_key="agent.responses"
            )
            
            executor.rabbit_channel.default_exchange.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling(self, orchestrator):
        """Test error handling in pipeline"""
        # Mock database error
        orchestrator.pg_pool.acquire.side_effect = Exception("Database connection failed")
        
        session_data = SessionCreate(user_id="test-user")
        
        with pytest.raises(Exception) as exc_info:
            await orchestrator.create_session(session_data)
        
        assert "Database connection failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, orchestrator):
        """Test handling concurrent requests"""
        sessions = []
        
        # Create multiple sessions concurrently
        for i in range(5):
            session_data = SessionCreate(user_id=f"user-{i}")
            sessions.append(orchestrator.create_session(session_data))
        
        results = await asyncio.gather(*sessions)
        
        assert len(results) == 5
        assert all(s.id for s in results)
    
    @pytest.mark.asyncio
    async def test_message_persistence(self, orchestrator):
        """Test message persistence in database"""
        session = await orchestrator.create_session(SessionCreate(user_id="test-user"))
        
        message = Message(
            session_id=session.id,
            role="user",
            content="Test message"
        )
        
        await orchestrator._store_message(message)
        
        # Verify database insert
        mock_conn = await orchestrator.pg_pool.acquire().__aenter__()
        mock_conn.execute.assert_called_with(
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
