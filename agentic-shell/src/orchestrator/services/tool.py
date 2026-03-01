"""
Tool Service
Manages tool registration and execution
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..models.tool import ToolInfo, ToolExecution, ToolResult, ToolType
from ..db.database import DatabasePool
from ..cache.redis import RedisClient
from ...tools.registry import tool_registry


class ToolService:
    """Service for managing tools"""
    
    def __init__(self, db_pool: DatabasePool, redis: RedisClient):
        self.db_pool = db_pool
        self.redis = redis
    
    async def list_tools(self) -> List[ToolInfo]:
        """List all available tools"""
        tools = []
        
        for name, tool_class in tool_registry.list_tools().items():
            tool = tool_class()
            tools.append(ToolInfo(
                name=name,
                type=self._get_tool_type(name),
                description=tool.description,
                version=getattr(tool, "version", "1.0.0"),
                enabled=await self._is_tool_enabled(name),
                commands=getattr(tool, "commands", []),
                rate_limit=getattr(tool, "rate_limit", None)
            ))
        
        return tools
    
    async def get_tool(self, tool_name: str) -> Optional[ToolInfo]:
        """Get detailed information about a specific tool"""
        tools = await self.list_tools()
        for tool in tools:
            if tool.name == tool_name:
                return tool
        return None
    
    async def execute_tool(self, tool_name: str, args: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a tool with given arguments"""
        # Get tool class
        tool_class = tool_registry.get_tool(tool_name)
        if not tool_class:
            raise ValueError(f"Tool not found: {tool_name}")
        
        # Check if tool is enabled
        if not await self._is_tool_enabled(tool_name):
            raise ValueError(f"Tool is disabled: {tool_name}")
        
        # Check rate limit
        if not await self._check_rate_limit(tool_name, user_id):
            raise ValueError(f"Rate limit exceeded for tool: {tool_name}")
        
        # Execute tool
        tool = tool_class()
        start_time = datetime.now()
        
        try:
            if asyncio.iscoroutinefunction(tool.execute):
                result = await tool.execute(**args)
            else:
                result = await asyncio.to_thread(tool.execute, **args)
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log execution
            await self._log_execution(ToolExecution(
                id=f"exec_{datetime.now().timestamp()}",
                tool_name=tool_name,
                arguments=args,
                user_id=user_id,
                status="completed",
                result=result,
                duration_ms=int(duration),
                created_at=start_time,
                completed_at=datetime.now()
            ))
            
            return result
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            await self._log_execution(ToolExecution(
                id=f"exec_{datetime.now().timestamp()}",
                tool_name=tool_name,
                arguments=args,
                user_id=user_id,
                status="failed",
                error=str(e),
                duration_ms=int(duration),
                created_at=start_time,
                completed_at=datetime.now()
            ))
            
            raise
    
    async def save_execution(self, execution: ToolExecution) -> None:
        """Save tool execution to database"""
        await self._log_execution(execution)
    
    async def get_execution_history(self, user_id: Optional[str] = None, tool_name: Optional[str] = None, limit: int = 100) -> List[ToolExecution]:
        """Get tool execution history"""
        # In production, this would query a database
        # For now, return from Redis cache
        key = f"tools:executions"
        if user_id:
            key += f":user:{user_id}"
        if tool_name:
            key += f":tool:{tool_name}"
        
        executions = await self.redis.lrange(key, 0, limit - 1)
        return [ToolExecution.parse_raw(exec) for exec in executions]
    
    async def get_execution(self, execution_id: str) -> Optional[ToolExecution]:
        """Get details of a specific tool execution"""
        # In production, this would query a database
        key = f"tools:execution:{execution_id}"
        data = await self.redis.get(key)
        if data:
            return ToolExecution.parse_raw(data)
        return None
    
    async def set_tool_enabled(self, tool_name: str, enabled: bool) -> None:
        """Enable or disable a tool"""
        await self.redis.set(f"tools:enabled:{tool_name}", str(enabled).lower())
    
    async def _is_tool_enabled(self, tool_name: str) -> bool:
        """Check if a tool is enabled"""
        enabled = await self.redis.get(f"tools:enabled:{tool_name}")
        if enabled is None:
            return True  # Default to enabled
        return enabled.lower() == "true"
    
    async def _check_rate_limit(self, tool_name: str, user_id: Optional[str]) -> bool:
        """Check rate limit for tool"""
        # In production, implement proper rate limiting
        return True
    
    async def _log_execution(self, execution: ToolExecution) -> None:
        """Log tool execution to Redis and database"""
        # Store in Redis list
        await self.redis.lpush(
            f"tools:executions",
            execution.json()
        )
        await self.redis.ltrim(f"tools:executions", 0, 999)
        
        # Store by execution ID
        await self.redis.setex(
            f"tools:execution:{execution.id}",
            86400,  # 24 hours
            execution.json()
        )
        
        # Store in database (async)
        asyncio.create_task(self._save_to_database(execution))
    
    async def _save_to_database(self, execution: ToolExecution) -> None:
        """Save execution to PostgreSQL"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO tool_executions (
                    id, tool_name, arguments, user_id, session_id,
                    status, result, error, duration_ms, created_at, completed_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
                execution.id,
                execution.tool_name,
                json.dumps(execution.arguments),
                execution.user_id,
                execution.session_id,
                execution.status,
                json.dumps(execution.result) if execution.result else None,
                execution.error,
                execution.duration_ms,
                execution.created_at,
                execution.completed_at
            )
    
    def _get_tool_type(self, tool_name: str) -> ToolType:
        """Determine tool type from name"""
        cloud_tools = ["aws", "gcp", "azure"]
        api_tools = ["github", "gitlab", "jira", "slack"]
        system_tools = ["kubernetes", "docker", "shell"]
        
        if tool_name in cloud_tools:
            return ToolType.CLOUD
        elif tool_name in api_tools:
            return ToolType.API
        elif tool_name in system_tools:
            return ToolType.SYSTEM
        else:
            return ToolType.CUSTOM