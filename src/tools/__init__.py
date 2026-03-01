"""
Tools Package
Tool implementations for agent capabilities
"""

from .registry import tool_registry
from .shell import Tool as ShellTool
from .kubernetes import Tool as KubernetesTool
from .docker import Tool as DockerTool
from .aws import Tool as AWSTool
from .github import Tool as GitHubTool

# Register tools
tool_registry.register("shell", ShellTool)
tool_registry.register("kubernetes", KubernetesTool)
tool_registry.register("docker", DockerTool)
tool_registry.register("aws", AWSTool)
tool_registry.register("github", GitHubTool)

__all__ = [
    "tool_registry",
    "ShellTool",
    "KubernetesTool",
    "DockerTool",
    "AWSTool",
    "GitHubTool",
]