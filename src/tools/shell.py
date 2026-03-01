"""Shell tool — execute shell commands in a subprocess."""
import asyncio
from typing import Any


async def run_command(command: str, timeout: int = 30) -> dict[str, Any]:
    """Run a shell command and return stdout, stderr, and return code.

    Warning: callers are responsible for sanitizing ``command`` to prevent
    shell injection before passing it to this function.
    """
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return {"returncode": -1, "stdout": "", "stderr": "Command timed out"}
    return {
        "returncode": proc.returncode,
        "stdout": stdout.decode(),
        "stderr": stderr.decode(),
    }
