"""
Docker Tool - Manage Docker containers
"""

import asyncio
import json
import subprocess
from typing import Dict, Any, List, Optional


class Tool:
    """Docker management tool"""
    
    def __init__(self):
        self.name = "docker"
        self.description = "Manage Docker containers"
        self.version = "1.0.0"
        self.commands = ["run", "exec", "build", "push", "pull", "ps", "images"]
        
    async def execute(self, cmd: str, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute docker command
        
        Args:
            cmd: Docker command (run, exec, build, etc.)
            *args: Command arguments
            **kwargs: Additional options
            
        Returns:
            Dict with stdout, stderr, returncode
        """
        # Build docker command
        docker_cmd = ["docker", cmd]
        
        # Add options
        for key, value in kwargs.items():
            if value is True:
                docker_cmd.append(f"--{key}")
            elif value is not None and value is not False:
                docker_cmd.extend([f"--{key}", str(value)])
        
        # Add arguments
        docker_cmd.extend([str(arg) for arg in args])
        
        try:
            process = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            result = {
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "returncode": process.returncode,
                "command": " ".join(docker_cmd)
            }
            
            # Try to parse JSON output
            if result["stdout"] and result["stdout"].strip().startswith(("[", "{")):
                try:
                    result["parsed"] = json.loads(result["stdout"])
                except:
                    pass
            
            return result
            
        except Exception as e:
            return {
                "error": str(e),
                "command": " ".join(docker_cmd),
                "returncode": -1
            }
    
    async def ps(self, all: bool = False, **kwargs) -> Dict[str, Any]:
        """List containers"""
        return await self.execute("ps", *(["-a"] if all else []), **kwargs)
    
    async def images(self, **kwargs) -> Dict[str, Any]:
        """List images"""
        return await self.execute("images", **kwargs)
    
    async def pull(self, image: str, **kwargs) -> Dict[str, Any]:
        """Pull an image"""
        return await self.execute("pull", image, **kwargs)
    
    async def run(self, image: str, command: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Run a container"""
        args = []
        if command:
            args.append(command)
        return await self.execute("run", image, *args, **kwargs)
    
    async def exec(self, container: str, command: str, **kwargs) -> Dict[str, Any]:
        """Execute command in container"""
        return await self.execute("exec", container, command, **kwargs)
    
    async def build(self, path: str = ".", tag: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Build an image"""
        if tag:
            kwargs["tag"] = tag
        return await self.execute("build", path, **kwargs)
    
    async def push(self, image: str, **kwargs) -> Dict[str, Any]:
        """Push an image"""
        return await self.execute("push", image, **kwargs)
    
    async def stop(self, container: str, **kwargs) -> Dict[str, Any]:
        """Stop a container"""
        return await self.execute("stop", container, **kwargs)
    
    async def rm(self, container: str, **kwargs) -> Dict[str, Any]:
        """Remove a container"""
        return await self.execute("rm", container, **kwargs)
    
    async def rmi(self, image: str, **kwargs) -> Dict[str, Any]:
        """Remove an image"""
        return await self.execute("rmi", image, **kwargs)