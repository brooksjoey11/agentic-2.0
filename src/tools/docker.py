"""Docker tool — manage Docker containers and images."""
import subprocess
from typing import Any


def run_container(image: str, command: str = "", env: dict[str, str] | None = None) -> dict[str, Any]:
    cmd = ["docker", "run", "--rm"]
    for key, value in (env or {}).items():
        cmd += ["-e", f"{key}={value}"]
    cmd.append(image)
    if command:
        cmd += command.split()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def list_containers(all_containers: bool = False) -> list[dict[str, Any]]:
    cmd = ["docker", "ps", "--format", "{{.ID}}\t{{.Image}}\t{{.Status}}"]
    if all_containers:
        cmd.append("-a")
    result = subprocess.run(cmd, capture_output=True, text=True)
    containers = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            containers.append({"id": parts[0], "image": parts[1], "status": parts[2]})
    return containers
