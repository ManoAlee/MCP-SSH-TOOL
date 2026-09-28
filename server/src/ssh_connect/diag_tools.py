"""
Advanced Diagnostic Tools Module
Docker inspection, listening ports & sockets scan, elevated sudo execution.
"""

import json
import logging
from typing import Optional, Dict, Any, List
import paramiko

from .pool import HostSession
from .security import ps_esc, smart_truncate

logger = logging.getLogger("ssh-connect")


async def execute_sudo(
    session: HostSession,
    command: str,
    sudo_password: Optional[str] = None,
    timeout: int = 60
) -> Dict[str, Any]:
    if session.mode != "ssh" or not session.ssh_client:
        raise ValueError("sudo_execute is only supported in SSH Linux mode")
        
    passwd = sudo_password or session.password or ""
    full_cmd = f"sudo -S -p '' {command}"
    stdin, stdout, stderr = session.ssh_client.exec_command(full_cmd, timeout=timeout, get_pty=True)
    
    if passwd:
        stdin.write(f"{passwd}\n")
        stdin.flush()
        
    stdout_data = stdout.read().decode("utf-8", errors="replace")
    exit_status = stdout.channel.recv_exit_status()
    
    return {
        "command": command,
        "exit_status": exit_status,
        "stdout": smart_truncate(stdout_data),
    }


async def inspect_docker(
    session: HostSession,
    action: str = "ps",
    target: Optional[str] = None,
    tail: int = 50
) -> str:
    if session.mode != "ssh" or not session.ssh_client:
        raise ValueError("docker_inspect is currently supported on Linux SSH hosts with Docker installed")
        
    if action == "ps":
        cmd = "docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'"
    elif action == "ps_all":
        cmd = "docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'"
    elif action == "stats":
        cmd = "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}'"
    elif action == "logs":
        if not target:
            raise ValueError("Target container name or ID is required for 'logs' action")
        cmd = f"docker logs --tail {int(tail)} '{target}'"
    elif action == "inspect":
        if not target:
            raise ValueError("Target container name or ID is required for 'inspect' action")
        cmd = f"docker inspect '{target}'"
    else:
        raise ValueError(f"Unknown docker action: {action}. Options: ps, ps_all, stats, logs, inspect")

    stdin, stdout, stderr = session.ssh_client.exec_command(cmd, timeout=30)
    stdout_data = stdout.read().decode("utf-8", errors="replace")
    stderr_data = stderr.read().decode("utf-8", errors="replace")
    exit_status = stdout.channel.recv_exit_status()
    
    if exit_status != 0 and stderr_data:
        if "permission denied" in stderr_data.lower():
            return f"Permission Denied: User '{session.username}' does not have permissions to access docker daemon. Use sudo_execute or add user to docker group."
        return f"Docker Error ({exit_status}): {stderr_data}"
        
    return smart_truncate(stdout_data or stderr_data)


async def scan_listening_ports(
    session: HostSession,
    protocol: str = "all"
) -> str:
    if session.mode == "ssh":
        if not session.ssh_client:
            raise ValueError("SSH client not connected")
        cmd = "ss -tulnp 2>/dev/null || netstat -tulnp 2>/dev/null || netstat -an"
        stdin, stdout, stderr = session.ssh_client.exec_command(cmd, timeout=20)
        out = stdout.read().decode("utf-8", errors="replace")
        return smart_truncate(out)
        
    elif session.mode == "powershell":
        from .server import run_powershell_async
        ps_cmd = "Get-NetTCPConnection -State Listen | Select-Object LocalAddress, LocalPort, OwningProcess | Sort-Object LocalPort | ConvertTo-Json -Compress"
        exit_code, stdout, stderr = await run_powershell_async(ps_cmd, timeout=20)
        if exit_code != 0:
            return f"Failed to retrieve ports: {stderr or stdout}"
        return stdout
    else:
        raise ValueError(f"Unsupported session mode: {session.mode}")
