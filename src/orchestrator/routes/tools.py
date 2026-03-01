"""
Tool Management Routes
Handles tool registration, execution, and monitoring
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..models.tool import ToolInfo, ToolExecution, ToolResult
from ..services.tool import ToolService
from ..dependencies import get_tool_service
from ..auth import get_current_user, require_admin

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=List[ToolInfo])
async def list_tools(
    tool_service: ToolService = Depends(get_tool_service)
):
    """List all available tools"""
    return await tool_service.list_tools()


@router.get("/{tool_name}", response_model=ToolInfo)
async def get_tool(
    tool_name: str,
    tool_service: ToolService = Depends(get_tool_service)
):
    """Get detailed information about a specific tool"""
    tool = await tool_service.get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool


@router.post("/{tool_name}/execute")
async def execute_tool(
    tool_name: str,
    args: Dict[str, Any],
    background_tasks: BackgroundTasks,
    tool_service: ToolService = Depends(get_tool_service),
    user_id: Optional[str] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Execute a tool with given arguments"""
    # Create execution record
    execution = ToolExecution(
        id=f"exec_{datetime.now().timestamp()}",
        tool_name=tool_name,
        arguments=args,
        user_id=user_id,
        status="pending",
        created_at=datetime.now()
    )
    
    # Execute tool
    try:
        result = await tool_service.execute_tool(tool_name, args, user_id)
        
        # Update execution record
        execution.status = "completed"
        execution.result = result
        execution.completed_at = datetime.now()
        
        # Background task to save execution history
        background_tasks.add_task(tool_service.save_execution, execution)
        
        return {
            "execution_id": execution.id,
            "status": "completed",
            "result": result
        }
        
    except Exception as e:
        execution.status = "failed"
        execution.error = str(e)
        execution.completed_at = datetime.now()
        
        background_tasks.add_task(tool_service.save_execution, execution)
        
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")


@router.get("/executions/history")
async def get_execution_history(
    tool_name: Optional[str] = None,
    limit: int = 100,
    tool_service: ToolService = Depends(get_tool_service),
    user_id: Optional[str] = Depends(get_current_user)
) -> List[ToolExecution]:
    """Get tool execution history"""
    return await tool_service.get_execution_history(user_id, tool_name, limit)


@router.get("/executions/{execution_id}")
async def get_execution(
    execution_id: str,
    tool_service: ToolService = Depends(get_tool_service)
) -> ToolExecution:
    """Get details of a specific tool execution"""
    execution = await tool_service.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


@router.post("/{tool_name}/enable")
async def enable_tool(
    tool_name: str,
    tool_service: ToolService = Depends(get_tool_service),
    _: bool = Depends(require_admin)
):
    """Enable a tool (admin only)"""
    await tool_service.set_tool_enabled(tool_name, True)
    return {"status": "enabled", "tool": tool_name}


@router.post("/{tool_name}/disable")
async def disable_tool(
    tool_name: str,
    tool_service: ToolService = Depends(get_tool_service),
    _: bool = Depends(require_admin)
):
    """Disable a tool (admin only)"""
    await tool_service.set_tool_enabled(tool_name, False)
    return {"status": "disabled", "tool": tool_name}