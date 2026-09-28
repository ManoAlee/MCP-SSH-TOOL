"""
Remote File Operations Module
High-performance SFTP and Windows UNC/C$ operations: reading slice with line numbers,
direct writing, tailing logs, directory listing, upload, and download.
"""

import os
import shutil
import base64
import logging
from typing import Optional, Dict, Any, List
import paramiko

from .security import ps_esc, smart_truncate
from .pool import HostSession

logger = logging.getLogger("ssh-connect")


def get_unc_path(host: str, path: str) -> str:
    if path.startswith("\\\\"):
        return path
    if len(path) >= 2 and path[1] == ":" and path[0].isalpha():
        drive = path[0].lower()
        rest = path[2:].lstrip("\\/")
        return f"\\\\{host}\\{drive}$\\{rest}"
    return f"\\\\{host}\\c$\\{path.lstrip('\\/')}"


def is_local_host(host: Optional[str]) -> bool:
    if not host:
        return False
    h = host.lower()
    local_names = {"localhost", "127.0.0.1", "."}
    try:
        import socket
        local_names.add(socket.gethostname().lower())
    except:
        pass
    return h in local_names


async def read_remote_file_content(
    session: HostSession,
    remote_path: str,
    start_line: int = 1,
    end_line: Optional[int] = None,
    max_lines: int = 500
) -> str:
    if session.mode == "ssh":
        if not session.sftp_client:
            raise ValueError("SFTP client not connected")
            
        try:
            with session.sftp_client.open(remote_path, "r") as f:
                content = f.read().decode("utf-8", errors="replace")
        except Exception as e:
            if session.ssh_client:
                stdin, stdout, stderr = session.ssh_client.exec_command(f"cat '{remote_path}'", timeout=15)
                content = stdout.read().decode("utf-8", errors="replace")
                if not content and stderr.read():
                    raise ValueError(f"Failed to read file: {stderr.read().decode('utf-8')}")
            else:
                raise ValueError(f"SFTP read failed: {str(e)}")
                
    elif session.mode == "powershell":
        unc = get_unc_path(session.host, remote_path)
        if os.path.isfile(unc):
            with open(unc, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        else:
            from .server import run_powershell_async
            ps_cmd = f"Get-Content -Path '{ps_esc(remote_path)}' -Raw"
            if not is_local_host(session.host) and session.username and session.password:
                full_cmd = f"""
                $secpasswd = ConvertTo-SecureString '{ps_esc(session.password)}' -AsPlainText -Force
                $creds = New-Object System.Management.Automation.PSCredential ('{ps_esc(session.username)}', $secpasswd)
                Invoke-Command -ComputerName '{ps_esc(session.host)}' -Credential $creds -ScriptBlock {{ {ps_cmd} }}
                """
            else:
                full_cmd = ps_cmd
            exit_code, stdout, stderr = await run_powershell_async(full_cmd, timeout=20)
            if exit_code != 0:
                raise ValueError(f"Failed to read file via PowerShell: {stderr or stdout}")
            content = stdout
    else:
        raise ValueError(f"Unsupported session mode: {session.mode}")

    lines = content.splitlines()
    total_lines = len(lines)
    
    start_idx = max(1, start_line) - 1
    end_idx = min(total_lines, end_line) if end_line else min(total_lines, start_idx + max_lines)
    
    selected_lines = lines[start_idx:end_idx]
    
    formatted_lines = []
    for i, line in enumerate(selected_lines, start=start_idx + 1):
        formatted_lines.append(f"{i}: {line}")
        
    header = f"File: {remote_path} (Showing lines {start_idx + 1} to {end_idx} of {total_lines} total lines):\n"
    return header + "\n".join(formatted_lines)


async def write_remote_file_content(
    session: HostSession,
    remote_path: str,
    content: str,
    append: bool = False
) -> str:
    if session.mode == "ssh":
        if not session.sftp_client:
            raise ValueError("SFTP client not connected")
            
        mode = "a" if append else "w"
        parent_dir = os.path.dirname(remote_path).replace("\\", "/")
        if parent_dir and session.ssh_client:
            session.ssh_client.exec_command(f"mkdir -p '{parent_dir}'", timeout=10)
            
        with session.sftp_client.open(remote_path, mode) as f:
            f.write(content.encode("utf-8"))
            
        return f"Successfully {'appended to' if append else 'wrote'} {len(content)} characters to {remote_path}"
        
    elif session.mode == "powershell":
        unc = get_unc_path(session.host, remote_path)
        try:
            os.makedirs(os.path.dirname(unc), exist_ok=True)
            mode = "a" if append else "w"
            with open(unc, mode, encoding="utf-8") as f:
                f.write(content)
            return f"Successfully {'appended to' if append else 'wrote'} {len(content)} characters to {remote_path} via UNC share"
        except Exception as e:
            from .server import run_powershell_async
            b64_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
            ps_cmd = f"[System.IO.File]::WriteAllText('{ps_esc(remote_path)}', [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{b64_content}')))"
            exit_code, stdout, stderr = await run_powershell_async(ps_cmd, timeout=30)
            if exit_code != 0:
                raise ValueError(f"Failed to write file via PowerShell: {stderr or stdout}")
            return f"Successfully wrote to {remote_path} via PowerShell"
    else:
        raise ValueError(f"Unsupported session mode: {session.mode}")


async def tail_remote_log_content(
    session: HostSession,
    remote_path: str,
    lines: int = 50
) -> str:
    if session.mode == "ssh":
        if not session.ssh_client:
            raise ValueError("SSH client not connected")
        cmd = f"tail -n {int(lines)} '{remote_path}'"
        stdin, stdout, stderr = session.ssh_client.exec_command(cmd, timeout=15)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        if not out and err:
            raise ValueError(f"Failed to tail log: {err}")
        return out
        
    elif session.mode == "powershell":
        from .server import run_powershell_async
        ps_cmd = f"Get-Content -Path '{ps_esc(remote_path)}' -Tail {int(lines)}"
        if not is_local_host(session.host) and session.username and session.password:
            full_cmd = f"""
            $secpasswd = ConvertTo-SecureString '{ps_esc(session.password)}' -AsPlainText -Force
            $creds = New-Object System.Management.Automation.PSCredential ('{ps_esc(session.username)}', $secpasswd)
            Invoke-Command -ComputerName '{ps_esc(session.host)}' -Credential $creds -ScriptBlock {{ {ps_cmd} }}
            """
        else:
            full_cmd = ps_cmd
        exit_code, stdout, stderr = await run_powershell_async(full_cmd, timeout=20)
        if exit_code != 0:
            raise ValueError(f"Failed to tail log: {stderr or stdout}")
        return stdout
    else:
        raise ValueError(f"Unsupported session mode: {session.mode}")
