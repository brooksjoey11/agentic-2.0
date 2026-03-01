"""
Agent Management Routes
Handles agent status, metrics, and control
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Any
from datetime import datetime, timedelta

from ..models.agent import AgentInfo, AgentMetrics, AgentControl
from ..services.agent import AgentService
from ..dependencies import get_agent_service
from ..auth import require_admin

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=List[AgentInfo])
async def list_agents(
    agent_service: AgentService = Depends(get_agent_service)
):
    """List all registered agents with their status"""
    return await agent_service.list_agents()


@router.get("/{agent_type}", response_model=AgentInfo)
async def get_agent(
    agent_type: str,
    agent_service: AgentService = Depends(get_agent_service)
):
    """Get detailed information about a specific agent"""
    agent = await agent_service.get_agent(agent_type)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/{agent_type}/metrics", response_model=AgentMetrics)
async def get_agent_metrics(
    agent_type: str,
    hours: int = 24,
    agent_service: AgentService = Depends(get_agent_service)
):
    """Get performance metrics for a specific agent"""
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    return await agent_service.get_metrics(agent_type, start_time, end_time)


@router.post("/{agent_type}/control")
async def control_agent(
    agent_type: str,
    control: AgentControl,
    agent_service: AgentService = Depends(get_agent_service),
    _: bool = Depends(require_admin)
):
    """Control an agent (start, stop, restart, scale)"""
    result = await agent_service.control_agent(agent_type, control)
    return {"status": "success", "agent": agent_type, "action": control.action, "result": result}


@router.get("/stats/summary")
async def get_agent_summary(
    agent_service: AgentService = Depends(get_agent_service)
) -> Dict[str, Any]:
    """Get summary statistics for all agents"""
    agents = await agent_service.list_agents()
    
    total_tasks = sum(a.tasks_completed for a in agents)
    total_errors = sum(a.tasks_failed for a in agents)
    active_agents = sum(1 for a in agents if a.status == "active")
    
    return {
        "total_agents": len(agents),
        "active_agents": active_agents,
        "total_tasks": total_tasks,
        "total_errors": total_errors,
        "error_rate": (total_errors / total_tasks * 100) if total_tasks > 0 else 0,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/queue/depth")
async def get_queue_depth(
    agent_service: AgentService = Depends(get_agent_service)
) -> Dict[str, int]:
    """Get current queue depth for each agent type"""
    return await agent_service.get_queue_depths()