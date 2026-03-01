"""Agent service logic."""
from src.orchestrator.models.agent import Agent, AgentCreate


async def create_agent(payload: AgentCreate) -> Agent:
    return Agent(id="placeholder", **payload.model_dump())


async def get_agent(agent_id: str) -> Agent | None:
    return None


async def list_agents() -> list[Agent]:
    return []


async def delete_agent(agent_id: str) -> bool:
    return True
