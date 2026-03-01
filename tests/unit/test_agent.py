"""Unit tests for base and concrete agent classes."""
import pytest

from src.agents.base import BaseAgent
from src.agents.planner import PlannerAgent
from src.agents.executor import ExecutorAgent
from src.agents.coder import CoderAgent
from src.agents.debugger import DebuggerAgent
from src.agents.optimizer import OptimizerAgent
from src.agents.reflector import ReflectorAgent
from src.agents.worker import WorkerAgent


class ConcreteAgent(BaseAgent):
    async def run(self, task):
        return {"done": True}


@pytest.mark.asyncio
async def test_base_agent_run():
    agent = ConcreteAgent(name="test")
    result = await agent.run({})
    assert result == {"done": True}


@pytest.mark.asyncio
async def test_planner_agent():
    agent = PlannerAgent(name="planner")
    result = await agent.run({"goal": "deploy app"})
    assert "plan" in result
    assert result["goal"] == "deploy app"


@pytest.mark.asyncio
async def test_executor_agent():
    agent = ExecutorAgent(name="executor")
    result = await agent.run({"steps": [{"action": "build"}]})
    assert "results" in result
    assert len(result["results"]) == 1


@pytest.mark.asyncio
async def test_coder_agent():
    agent = CoderAgent(name="coder")
    result = await agent.run({"spec": "write a hello world function"})
    assert "code" in result


@pytest.mark.asyncio
async def test_debugger_agent():
    agent = DebuggerAgent(name="debugger")
    result = await agent.run({"error": "AttributeError: NoneType"})
    assert "suggested_fix" in result


@pytest.mark.asyncio
async def test_optimizer_agent():
    agent = OptimizerAgent(name="optimizer")
    result = await agent.run({"target": "slow_function"})
    assert "optimised" in result


@pytest.mark.asyncio
async def test_reflector_agent():
    agent = ReflectorAgent(name="reflector")
    result = await agent.run({"outcome": {"status": "success"}})
    assert "insights" in result


@pytest.mark.asyncio
async def test_worker_agent():
    agent = WorkerAgent(name="worker")
    result = await agent.run({"type": "shell", "command": "echo hi"})
    assert result["status"] == "completed"
