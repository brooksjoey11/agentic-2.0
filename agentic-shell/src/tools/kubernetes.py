"""
Kubernetes tool - Manage Kubernetes clusters
"""

import asyncio
import json
import subprocess
from typing import Dict, Any, List, Optional
import yaml

class Tool:
    """Kubernetes management tool"""
    
    def __init__(self):
        self.name = "kubernetes"
        self.description = "Manage Kubernetes clusters"
        self.kubeconfig = None
        
    async def execute(self, 
                      cmd: str,
                      namespace: Optional[str] = None,
                      context: Optional[str] = None,
                      output_format: str = "yaml") -> Dict[str, Any]:
        """
        Execute kubectl command
        
        Args:
            cmd: kubectl command (e.g., "get pods")
            namespace: Kubernetes namespace
            context: Kubernetes context
            output_format: Output format (yaml, json, wide)
            
        Returns:
            Dict with stdout, stderr, returncode
        """
        # Build kubectl command
        kubectl_cmd = ["kubectl"]
        
        if context:
            kubectl_cmd.extend(["--context", context])
        
        if namespace:
            kubectl_cmd.extend(["-n", namespace])
        
        # Add the actual command
        kubectl_cmd.extend(cmd.split())
        
        if output_format and "-o" not in cmd:
            kubectl_cmd.extend(["-o", output_format])
        
        try:
            process = await asyncio.create_subprocess_exec(
                *kubectl_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            result = {
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "returncode": process.returncode,
                "command": " ".join(kubectl_cmd)
            }
            
            # Try to parse output if it's JSON
            if output_format == "json" and result["stdout"]:
                try:
                    result["parsed"] = json.loads(result["stdout"])
                except:
                    pass
            
            return result
            
        except Exception as e:
            return {
                "error": str(e),
                "command": " ".join(kubectl_cmd),
                "returncode": -1
            }
    
    async def get_pods(self, namespace: str = "default", **kwargs) -> Dict[str, Any]:
        """Get pods in namespace"""
        return await self.execute(f"get pods", namespace=namespace, **kwargs)
    
    async def get_services(self, namespace: str = "default", **kwargs) -> Dict[str, Any]:
        """Get services in namespace"""
        return await self.execute(f"get services", namespace=namespace, **kwargs)
    
    async def get_deployments(self, namespace: str = "default", **kwargs) -> Dict[str, Any]:
        """Get deployments in namespace"""
        return await self.execute(f"get deployments", namespace=namespace, **kwargs)
    
    async def get_nodes(self, **kwargs) -> Dict[str, Any]:
        """Get cluster nodes"""
        return await self.execute("get nodes", **kwargs)
    
    async def apply(self, manifest: str, **kwargs) -> Dict[str, Any]:
        """Apply a manifest"""
        # Write manifest to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(manifest)
            temp_file = f.name
        
        try:
            result = await self.execute(f"apply -f {temp_file}", **kwargs)
        finally:
            import os
            os.unlink(temp_file)
        
        return result
    
    async def delete(self, resource_type: str, name: str, namespace: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Delete a resource"""
        cmd = f"delete {resource_type} {name}"
        return await self.execute(cmd, namespace=namespace, **kwargs)
    
    async def logs(self, pod: str, container: Optional[str] = None, tail: int = 100, **kwargs) -> Dict[str, Any]:
        """Get pod logs"""
        cmd = f"logs {pod}"
        if container:
            cmd += f" -c {container}"
        if tail:
            cmd += f" --tail={tail}"
        
        return await self.execute(cmd, output_format="", **kwargs)
    
    async def exec(self, pod: str, command: str, container: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Execute command in pod"""
        cmd = f"exec {pod} -- {command}"
        if container:
            cmd = f"exec {pod} -c {container} -- {command}"
        
        return await self.execute(cmd, output_format="", **kwargs)