"""
GitHub Tool - Manage GitHub repositories and operations
"""

import asyncio
import json
import subprocess
from typing import Dict, Any, List, Optional


class Tool:
    """GitHub management tool"""
    
    def __init__(self):
        self.name = "github"
        self.description = "Manage GitHub repositories"
        self.version = "1.0.0"
        self.commands = ["repo", "pr", "issue", "actions", "release"]
        
    async def execute(self, cmd: str, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute gh command
        
        Args:
            cmd: GitHub command (repo, pr, issue, etc.)
            *args: Command arguments
            **kwargs: Additional options
            
        Returns:
            Dict with stdout, stderr, returncode
        """
        # Build gh command
        gh_cmd = ["gh", cmd]
        
        # Add arguments
        gh_cmd.extend([str(arg) for arg in args])
        
        # Add options
        for key, value in kwargs.items():
            if value is True:
                gh_cmd.append(f"--{key}")
            elif value is not None and value is not False:
                gh_cmd.extend([f"--{key}", str(value)])
        
        try:
            process = await asyncio.create_subprocess_exec(
                *gh_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            result = {
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "returncode": process.returncode,
                "command": " ".join(gh_cmd)
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
                "command": " ".join(gh_cmd),
                "returncode": -1
            }
    
    async def repo_list(self, **kwargs) -> Dict[str, Any]:
        """List repositories"""
        return await self.execute("repo", "list", **kwargs)
    
    async def repo_create(self, name: str, **kwargs) -> Dict[str, Any]:
        """Create a repository"""
        return await self.execute("repo", "create", name, **kwargs)
    
    async def repo_clone(self, repo: str, directory: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Clone a repository"""
        args = [repo]
        if directory:
            args.append(directory)
        return await self.execute("repo", "clone", *args, **kwargs)
    
    async def pr_list(self, **kwargs) -> Dict[str, Any]:
        """List pull requests"""
        return await self.execute("pr", "list", **kwargs)
    
    async def pr_create(self, title: str, body: str, **kwargs) -> Dict[str, Any]:
        """Create a pull request"""
        return await self.execute("pr", "create", "--title", title, "--body", body, **kwargs)
    
    async def pr_checkout(self, number: int, **kwargs) -> Dict[str, Any]:
        """Checkout a pull request"""
        return await self.execute("pr", "checkout", str(number), **kwargs)
    
    async def issue_list(self, **kwargs) -> Dict[str, Any]:
        """List issues"""
        return await self.execute("issue", "list", **kwargs)
    
    async def issue_create(self, title: str, body: str, **kwargs) -> Dict[str, Any]:
        """Create an issue"""
        return await self.execute("issue", "create", "--title", title, "--body", body, **kwargs)
    
    async def actions_list(self, **kwargs) -> Dict[str, Any]:
        """List workflow runs"""
        return await self.execute("run", "list", **kwargs)
    
    async def actions_run(self, workflow: str, **kwargs) -> Dict[str, Any]:
        """Run a workflow"""
        return await self.execute("workflow", "run", workflow, **kwargs)
    
    async def release_list(self, **kwargs) -> Dict[str, Any]:
        """List releases"""
        return await self.execute("release", "list", **kwargs)
    
    async def release_create(self, tag: str, title: str, **kwargs) -> Dict[str, Any]:
        """Create a release"""
        return await self.execute("release", "create", tag, "--title", title, **kwargs)