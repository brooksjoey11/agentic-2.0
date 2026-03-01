"""
AWS Tool - Manage AWS cloud services
"""

import asyncio
import json
import subprocess
from typing import Dict, Any, List, Optional


class Tool:
    """AWS management tool"""
    
    def __init__(self):
        self.name = "aws"
        self.description = "Manage AWS cloud services"
        self.version = "1.0.0"
        self.commands = ["ec2", "s3", "lambda", "cloudformation", "iam"]
        
    async def execute(self, service: str, cmd: str, region: Optional[str] = None, profile: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Execute AWS CLI command
        
        Args:
            service: AWS service (ec2, s3, lambda, etc.)
            cmd: Command to execute
            region: AWS region
            profile: AWS profile
            **kwargs: Additional arguments
            
        Returns:
            Dict with stdout, stderr, returncode
        """
        # Build AWS CLI command
        aws_cmd = ["aws", service, cmd]
        
        if region:
            aws_cmd.extend(["--region", region])
        
        if profile:
            aws_cmd.extend(["--profile", profile])
        
        # Add any additional args
        for key, value in kwargs.items():
            if value is True:
                aws_cmd.append(f"--{key}")
            elif value is not None and value is not False:
                aws_cmd.extend([f"--{key}", str(value)])
        
        try:
            process = await asyncio.create_subprocess_exec(
                *aws_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            result = {
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "returncode": process.returncode,
                "command": " ".join(aws_cmd)
            }
            
            # Try to parse JSON output
            if result["stdout"] and result["stdout"].strip().startswith(("{", "[")):
                try:
                    result["parsed"] = json.loads(result["stdout"])
                except:
                    pass
            
            return result
            
        except Exception as e:
            return {
                "error": str(e),
                "command": " ".join(aws_cmd),
                "returncode": -1
            }
    
    async def ec2_describe_instances(self, instance_ids: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """Describe EC2 instances"""
        cmd = "describe-instances"
        if instance_ids:
            kwargs["instance-ids"] = " ".join(instance_ids)
        return await self.execute("ec2", cmd, **kwargs)
    
    async def s3_list_buckets(self, **kwargs) -> Dict[str, Any]:
        """List S3 buckets"""
        return await self.execute("s3api", "list-buckets", **kwargs)
    
    async def lambda_list_functions(self, **kwargs) -> Dict[str, Any]:
        """List Lambda functions"""
        return await self.execute("lambda", "list-functions", **kwargs)
    
    async def cloudformation_list_stacks(self, **kwargs) -> Dict[str, Any]:
        """List CloudFormation stacks"""
        return await self.execute("cloudformation", "list-stacks", **kwargs)