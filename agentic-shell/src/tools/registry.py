"""
Tool Registry
Central registry for all available tools
"""

from typing import Dict, Type, Any, Optional


class ToolRegistry:
    """Registry for tool classes"""
    
    def __init__(self):
        self._tools: Dict[str, Type] = {}
    
    def register(self, name: str, tool_class: Type) -> None:
        """Register a tool class"""
        self._tools[name] = tool_class
    
    def get_tool(self, name: str) -> Optional[Type]:
        """Get tool class by name"""
        return self._tools.get(name)
    
    def list_tools(self) -> Dict[str, Type]:
        """List all registered tools"""
        return self._tools.copy()
    
    def unregister(self, name: str) -> None:
        """Unregister a tool"""
        self._tools.pop(name, None)


# Global tool registry instance
tool_registry = ToolRegistry()