"""
Base Agent Class
Abstract base class for all agent implementations
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
import json


class BaseAgent(ABC):
    """Base class for all agents"""
    
    def __init__(self, agent_type: str):
        self.agent_type = agent_type
        self.id = f"{agent_type}_{datetime.now().timestamp()}"
        self.host = None
        self.pid = None
        self.start_time = datetime.now()
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.current_task = None
        
    @abstractmethod
    async def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message - to be implemented by subclasses"""
        pass
    
    async def heartbeat(self) -> Dict[str, Any]:
        """Send heartbeat with current status"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        return {
            "agent_type": self.agent_type,
            "agent_id": self.id,
            "host": self.host,
            "pid": os.getpid(),
            "status": "active" if not self.current_task else "busy",
            "current_task": self.current_task,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "memory_usage_mb": process.memory_info().rss / 1024 / 1024,
            "cpu_usage_percent": process.cpu_percent(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "timestamp": datetime.now().isoformat()
        }
    
    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool - to be implemented by subclasses with tool registry"""
        raise NotImplementedError
    
    def log(self, level: str, message: str, **kwargs):
        """Log a message"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": self.agent_type,
            "agent_id": self.id,
            "level": level,
            "message": message,
            **kwargs
        }
        print(json.dumps(log_entry))