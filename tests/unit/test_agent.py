"""
Unit Tests for Agent Module
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.agents.base import BaseAgent
from src.agents.worker import (
    AgentWorker,
    PlannerAgent,
    ExecutorAgent,
    CoderAgent,
    DebuggerAgent,
    OptimizerAgent,
    ReflectorAgent
)


class TestBaseAgent:
    """Test base agent functionality"""
    
    def test_init(self):
        """Test agent initialization"""
        agent = BaseAgent("test-agent")
        assert agent.agent_type == "test-agent"
        assert agent.tasks_completed == 0
        assert agent.tasks_failed == 0
        assert agent.current_task is None
    
    @pytest.mark.asyncio
    async def test_heartbeat(self):
        """Test heartbeat generation"""
        agent = BaseAgent("test-agent")
        heartbeat = await agent.heartbeat()
        
        assert heartbeat["agent_type"] == "test-agent"
        assert "agent_id" in heartbeat
        assert "status" in heartbeat
        assert "memory_usage_mb" in heartbeat
        assert "cpu_usage_percent" in heartbeat
        assert "timestamp" in heartbeat
    
    def test_log(self):
        """Test logging"""
        agent = BaseAgent("test-agent")
        # Just verify it doesn't crash
        agent.log("info", "test message", extra="data")


class TestAgentWorker:
    """Test agent worker base class"""
    
    @pytest.fixture
    def worker(self):
        worker = AgentWorker("test")
        worker.redis = AsyncMock()
        worker.rabbit_channel = AsyncMock()
        worker.mistral = AsyncMock()
        return worker
    
    @pytest.mark.asyncio
    async def test_connect(self, worker):
        """Test connection establishment"""
        worker.redis.from_url = AsyncMock(return_value=worker.redis)
        worker.redis.ping = AsyncMock(return_value=True)
        
        await worker.connect()
        
        worker.redis.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_tool_success(self, worker):
        """Test successful tool execution"""
        mock_tool = AsyncMock()
        mock_tool.execute.return_value = {"stdout": "test output"}
        worker.tools = {"shell": mock_tool}
        
        result = await worker.execute_tool("shell", {"cmd": "echo test"})
        
        assert result == {"stdout": "test output"}
        mock_tool.execute.assert_called_once_with(cmd="echo test")
    
    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, worker):
        """Test tool execution with unknown tool"""
        worker.tools = {}
        
        result = await worker.execute_tool("unknown", {})
        
        assert "error" in result
        assert "not available" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_tool_error(self, worker):
        """Test tool execution with error"""
        mock_tool = AsyncMock()
        mock_tool.execute.side_effect = Exception("Tool error")
        worker.tools = {"shell": mock_tool}
        
        result = await worker.execute_tool("shell", {"cmd": "echo test"})
        
        assert "error" in result
        assert "Tool error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_call_mistral_success(self, worker):
        """Test successful Mistral API call"""
        mock_response = Mock()
        mock_response.outputs = [Mock(text="Test response")]
        worker.mistral.beta.conversations.start = AsyncMock(return_value=mock_response)
        
        result = await worker.call_mistral("Test prompt")
        
        assert result == "Test response"
        worker.mistral.beta.conversations.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_call_mistral_error(self, worker):
        """Test Mistral API error"""
        worker.mistral.beta.conversations.start = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        result = await worker.call_mistral("Test prompt")
        
        assert "Error: API Error" in result


class TestPlannerAgent:
    """Test planner agent"""
    
    @pytest.fixture
    def agent(self):
        agent = PlannerAgent()
        agent.call_mistral = AsyncMock(return_value='{"plan": ["step1", "step2"]}')
        return agent
    
    @pytest.mark.asyncio
    async def test_process(self, agent):
        """Test message processing"""
        data = {
            "session_id": "test",
            "message": {"content": "Plan this task"}
        }
        
        result = await agent.process(data)
        
        assert result["metadata"]["type"] == "plan"
        assert "content" in result
        agent.call_mistral.assert_called_once()


class TestExecutorAgent:
    """Test executor agent"""
    
    @pytest.fixture
    def agent(self):
        agent = ExecutorAgent()
        agent.execute_tool = AsyncMock(return_value={"stdout": "command output"})
        agent.call_mistral = AsyncMock(return_value="echo 'hello'")
        return agent
    
    @pytest.mark.asyncio
    async def test_process_tool_request(self, agent):
        """Test tool request processing"""
        data = {
            "session_id": "test",
            "message": {
                "content": 'TOOL:{"tool": "shell", "args": {"cmd": "echo test"}}'
            }
        }
        
        result = await agent.process(data)
        
        assert result["metadata"]["tool_execution"] == "shell"
        assert "content" in result
        agent.execute_tool.assert_called_once()
        agent.call_mistral.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_command_request(self, agent):
        """Test command request processing"""
        data = {
            "session_id": "test",
            "message": {"content": "Show current directory"}
        }
        
        result = await agent.process(data)
        
        assert result["metadata"]["type"] == "command"
        assert result["content"] == "echo 'hello'"
        agent.call_mistral.assert_called_once()
        agent.execute_tool.assert_not_called()


class TestCoderAgent:
    """Test coder agent"""
    
    @pytest.fixture
    def agent(self):
        agent = CoderAgent()
        agent.call_mistral = AsyncMock(return_value="def hello():\n    return 'world'")
        return agent
    
    @pytest.mark.asyncio
    async def test_process(self, agent):
        """Test code generation"""
        data = {
            "session_id": "test",
            "message": {"content": "Write hello world function"}
        }
        
        result = await agent.process(data)
        
        assert result["metadata"]["type"] == "code"
        assert "def hello()" in result["content"]
        agent.call_mistral.assert_called_once()


class TestDebuggerAgent:
    """Test debugger agent"""
    
    @pytest.fixture
    def agent(self):
        agent = DebuggerAgent()
        agent.call_mistral = AsyncMock(return_value="Fix the syntax error")
        return agent
    
    @pytest.mark.asyncio
    async def test_process(self, agent):
        """Test error analysis"""
        data = {
            "session_id": "test",
            "message": {"content": "Fix this error: SyntaxError"}
        }
        
        result = await agent.process(data)
        
        assert result["metadata"]["type"] == "debug"
        assert "Fix the syntax error" in result["content"]
        agent.call_mistral.assert_called_once()


class TestOptimizerAgent:
    """Test optimizer agent"""
    
    @pytest.fixture
    def agent(self):
        agent = OptimizerAgent()
        agent.call_mistral = AsyncMock(return_value="Add indexes to improve performance")
        return agent
    
    @pytest.mark.asyncio
    async def test_process(self, agent):
        """Test performance optimization"""
        data = {
            "session_id": "test",
            "message": {"content": "Optimize this query"}
        }
        
        result = await agent.process(data)
        
        assert result["metadata"]["type"] == "optimization"
        assert "Add indexes" in result["content"]
        agent.call_mistral.assert_called_once()


class TestReflectorAgent:
    """Test reflector agent"""
    
    @pytest.fixture
    def agent(self):
        agent = ReflectorAgent()
        agent.redis = AsyncMock()
        agent.redis.lrange = AsyncMock(return_value=[
            json.dumps({"role": "user", "content": "Previous message"})
        ])
        agent.call_mistral = AsyncMock(return_value="Based on history, I recommend...")
        return agent
    
    @pytest.mark.asyncio
    async def test_process_with_history(self, agent):
        """Test message processing with history"""
        data = {
            "session_id": "test",
            "message": {"content": "What should I do next?"}
        }
        
        result = await agent.process(data)
        
        assert result["metadata"]["type"] == "reflection"
        assert "Based on history" in result["content"]
        agent.redis.lrange.assert_called_once()
        agent.call_mistral.assert_called_once()
