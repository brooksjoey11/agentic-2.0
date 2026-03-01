"""
Shell tool - Execute shell commands
"""

import asyncio
import subprocess
import shlex
from typing import Dict, Any, List
import os

class Tool:
    """Shell command execution tool"""
    
    def __init__(self):
        self.name = "shell"
        self.description = "Execute shell commands"
        self.dangerous_commands = []  # Empty = no restrictions
        
    async def execute(self, cmd: str, working_dir: str = None, timeout: int = 300, env: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Execute a shell command
        
        Args:
            cmd: Command to execute
            working_dir: Working directory (default: /tmp)
            timeout: Timeout in seconds
            env: Environment variables
            
        Returns:
            Dict with stdout, stderr, returncode
        """
        working_dir = working_dir or "/tmp"
        env_vars = os.environ.copy()
        if env:
            env_vars.update(env)
        
        try:
            # Create process
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                env=env_vars,
                shell=True
            )
            
            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "error": f"Command timed out after {timeout}s",
                    "cmd": cmd,
                    "returncode": -1
                }
            
            return {
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "returncode": process.returncode,
                "cmd": cmd
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "cmd": cmd,
                "returncode": -1
            }
    
    async def execute_batch(self, commands: List[str], **kwargs) -> List[Dict[str, Any]]:
        """Execute multiple commands in sequence"""
        results = []
        for cmd in commands:
            result = await self.execute(cmd, **kwargs)
            results.append(result)
            if result.get("returncode", 0) != 0:
                break
        return results
    
    async def execute_pipeline(self, commands: List[str], **kwargs) -> Dict[str, Any]:
        """Execute a pipeline of commands (output of one is input to next)"""
        if not commands:
            return {"error": "No commands"}
        
        current_input = None
        final_result = None
        
        for cmd in commands:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdin=asyncio.subprocess.PIPE if current_input else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **kwargs
            )
            
            stdout, stderr = await process.communicate(input=current_input)
            current_input = stdout
            
            final_result = {
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "returncode": process.returncode
            }
            
            if process.returncode != 0:
                break
        
        return final_result