"""
Secure Shell Tool
Executes shell commands with strict security controls.
"""

import asyncio
import os
import shlex
import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field

from ..orchestrator.config import config

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when a command violates security policies."""
    pass


@dataclass
class CommandAllowlist:
    """Configuration for allowed commands."""
    
    # Default dangerous patterns (always blocked)
    DANGEROUS_PATTERNS: Set[str] = field(default_factory=lambda: {
        "rm -rf /",
        "rm -rf /*",
        ":(){ :|:& };:",  # Fork bomb
        "dd if=/dev/zero",
        "mkfs",
        "format",
        "fdisk",
        "chmod 777 /",
        "chown -R",
        "> /dev/sda",
        "| sh",
        "`",
        "$(",
        ";",
        "&&",
        "||",
    })
    
    # Allowed commands (must be explicitly configured)
    allowed_commands: Set[str] = field(default_factory=set)
    
    # Allowed command prefixes (e.g., "git", "docker")
    allowed_prefixes: Set[str] = field(default_factory=set)
    
    # Blocked commands (even if in allowed list)
    blocked_commands: Set[str] = field(default_factory=set)


class SecureShellTool:
    """
    Secure shell command execution with allowlist and validation.
    
    Features:
    - Command allowlist (configurable)
    - Dangerous pattern blocking
    - Argument validation
    - Timeout enforcement
    - Audit logging
    - Rate limiting integration
    """
    
    def __init__(self):
        self.name = "shell"
        self.description = "Secure shell command execution"
        self.version = "2.0.0"
        
        # Load configuration
        self.timeout = int(config.get("SHELL_TIMEOUT", "30"))
        self.working_dir = config.get("SHELL_WORKING_DIR", "/tmp")
        
        # Build allowlist from environment
        self.allowlist = CommandAllowlist(
            allowed_commands={c for c in config.get("SHELL_ALLOWED_COMMANDS", "").split(",") if c},
            allowed_prefixes={p for p in config.get("SHELL_ALLOWED_PREFIXES", "").split(",") if p},
            blocked_commands={c for c in config.get("SHELL_BLOCKED_COMMANDS", "").split(",") if c}
        )
    
    def _validate_command(self, cmd: str) -> None:
        """
        Validate command against security policies.
        
        Raises SecurityError if command is not allowed.
        """
        cmd_lower = cmd.lower().strip()
        
        # Check dangerous patterns
        for pattern in self.allowlist.DANGEROUS_PATTERNS:
            if pattern in cmd_lower:
                logger.warning(f"Blocked dangerous pattern: {pattern}")
                raise SecurityError(f"Command contains dangerous pattern: {pattern}")
        
        # Extract the base command (first token)
        tokens = shlex.split(cmd)
        if not tokens:
            raise SecurityError("Empty command")
        
        base_command = tokens[0]
        
        # Check blocked commands
        if base_command in self.allowlist.blocked_commands:
            logger.warning(f"Blocked command: {base_command}")
            raise SecurityError(f"Command '{base_command}' is blocked")
        
        # If allowlist is configured, enforce it
        if self.allowlist.allowed_commands or self.allowlist.allowed_prefixes:
            allowed = False
            
            # Check exact matches
            if base_command in self.allowlist.allowed_commands:
                allowed = True
            
            # Check prefix matches
            for prefix in self.allowlist.allowed_prefixes:
                if base_command.startswith(prefix):
                    allowed = True
                    break
            
            if not allowed:
                logger.warning(f"Command not in allowlist: {base_command}")
                raise SecurityError(
                    f"Command '{base_command}' is not allowed. "
                    f"Allowed: {self.allowlist.allowed_commands} "
                    f"Prefixes: {self.allowlist.allowed_prefixes}"
                )
    
    def _sanitize_for_audit(self, cmd: str) -> str:
        """Sanitize command for audit logging (remove sensitive args)."""
        # Remove potential secrets (e.g., passwords after -p flags)
        tokens = shlex.split(cmd)
        sanitized = []
        
        skip_next = False
        for token in tokens:
            if skip_next:
                sanitized.append("[REDACTED]")
                skip_next = False
                continue
            
            # Check for flags that might have sensitive values
            if token in ["-p", "--password", "--token", "--secret"]:
                sanitized.append(token)
                skip_next = True
            else:
                sanitized.append(token)
        
        return " ".join(sanitized)
    
    async def execute(
        self,
        cmd: str,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        working_dir: Optional[str] = None,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Execute a shell command with security controls.
        
        Args:
            cmd: Command to execute
            correlation_id: For tracing
            user_id: Who is executing
            session_id: Which session
            working_dir: Working directory (default: configured)
            timeout: Timeout in seconds (default: configured)
            env: Additional environment variables
        
        Returns:
            Dict with stdout, stderr, returncode
        """
        # Validate command
        try:
            self._validate_command(cmd)
        except SecurityError as e:
            logger.warning(f"Security violation: {e}")
            return {
                "error": str(e),
                "cmd": self._sanitize_for_audit(cmd),
                "returncode": -1,
                "security_blocked": True
            }
        
        # Set working directory
        work_dir = working_dir or self.working_dir
        cmd_timeout = timeout or self.timeout
        
        # Prepare environment
        env_vars = os.environ.copy()
        if env:
            env_vars.update(env)
        
        # Audit log
        logger.info(
            "Tool execution",
            extra={
                "tool": "shell",
                "cmd": self._sanitize_for_audit(cmd),
                "correlation_id": correlation_id,
                "user_id": user_id,
                "session_id": session_id,
                "working_dir": work_dir,
                "timeout": cmd_timeout
            }
        )
        
        try:
            # Use shlex to safely parse command
            args = shlex.split(cmd)
            
            # Execute with create_subprocess_exec (not shell)
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
                env=env_vars
            )
            
            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=cmd_timeout
                )
                
                result = {
                    "stdout": stdout.decode('utf-8', errors='replace'),
                    "stderr": stderr.decode('utf-8', errors='replace'),
                    "returncode": process.returncode,
                    "cmd": self._sanitize_for_audit(cmd),
                    "duration_ms": 0  # Will be set by caller
                }
                
                # Log result
                logger.info(
                    "Tool execution completed",
                    extra={
                        "tool": "shell",
                        "returncode": process.returncode,
                        "correlation_id": correlation_id
                    }
                )
                
                return result
                
            except asyncio.TimeoutError:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                logger.warning(f"Command timed out after {cmd_timeout}s")
                return {
                    "error": f"Command timed out after {cmd_timeout}s",
                    "cmd": self._sanitize_for_audit(cmd),
                    "returncode": -1
                }
                
        except Exception as e:
            logger.error(f"Command execution failed: {e}", exc_info=True)
            return {
                "error": str(e),
                "cmd": self._sanitize_for_audit(cmd),
                "returncode": -1
            }
    
    async def execute_batch(
        self,
        commands: List[str],
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Execute multiple commands in sequence."""
        results = []
        for cmd in commands:
            result = await self.execute(
                cmd,
                correlation_id=f"{correlation_id}_{len(results)}" if correlation_id else None,
                **kwargs
            )
            results.append(result)
            if result.get("returncode", 0) != 0:
                break
        return results


# Export as Tool for compatibility with registry
Tool = SecureShellTool