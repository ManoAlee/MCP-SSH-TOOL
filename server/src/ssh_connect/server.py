"""
Enterprise SSH & PowerShell MCP Server
Top-tier Model Context Protocol implementation for managing remote Linux servers (SSH)
and Windows Domain hosts (PowerShell / WinRM / SMB shares).
"""

import os
import sys
import json
import base64
import asyncio
import logging
import traceback
from typing import Any, Dict, List, Optional

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

try:
    from .config_resolver import resolve_ssh_config, get_default_ssh_config_paths
    from .security import (
        load_private_key,
        is_dangerous_command,
        smart_truncate,
        ps_esc
    )
    from .pool import ConnectionPool, HostSession
    from .file_tools import (
        read_remote_file_content,
        write_remote_file_content,
        tail_remote_log_content,
        get_unc_path,
        is_local_host
    )
    from .diag_tools import (
        execute_sudo,
        inspect_docker,
        scan_listening_ports
    )
except (ImportError, ValueError):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from ssh_connect.config_resolver import resolve_ssh_config, get_default_ssh_config_paths
    from ssh_connect.security import (
        load_private_key,
        is_dangerous_command,
        smart_truncate,
        ps_esc
    )
    from ssh_connect.pool import ConnectionPool, HostSession
    from ssh_connect.file_tools import (
        read_remote_file_content,
        write_remote_file_content,
        tail_remote_log_content,
        get_unc_path,
        is_local_host
    )
    from ssh_connect.diag_tools import (
        execute_sudo,
        inspect_docker,
        scan_listening_ports
    )

# -------------------------------------------------------------
# Environment & Logger Configuration
# -------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))

# Locate .env dynamically
env_candidates = [
    os.environ.get("SSH_MCP_ENV"),
    os.path.join(project_root, ".env"),
    os.path.join(project_root, "..", ".env"),
    r"C:\ssh-mcp\.env"
]
for env_path in env_candidates:
    if env_path and os.path.isfile(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip().strip("'\""))
            break
        except Exception:
            pass

SSH_HOST = os.environ.get("SSH_HOST", "")
SSH_PORT = int(os.environ.get("SSH_PORT", "22"))
SSH_USERNAME = os.environ.get("SSH_USERNAME", "")
SSH_PASSWORD = os.environ.get("SSH_PASSWORD", "")
SSH_KEY_PATH = os.environ.get("SSH_KEY_PATH", "")
SSH_KEY_PASSPHRASE = os.environ.get("SSH_KEY_PASSPHRASE", "")
CONNECTION_MODE = os.environ.get("CONNECTION_MODE", "ssh").lower()

default_log_dir = os.path.join(project_root, "logs")
try:
    os.makedirs(default_log_dir, exist_ok=True)
except Exception:
    pass

LOG_PATH = os.environ.get("SSH_MCP_LOG", os.path.join(default_log_dir, "ssh-mcp.log"))
logger = logging.getLogger("ssh-connect")
if not logger.handlers:
    try:
        handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
        fmt = logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s] %(message)s")
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    except Exception:
        pass

logger.info("=== Enterprise SSH-Connect & PowerShell MCP Server Initialized ===")

# Global Server & Pool
server = Server("ssh-connect")
pool = ConnectionPool()

# MCP 1.x / 2.x Compatibility Bridge
if not hasattr(server, "list_tools"):
    def _compat_list_tools():
        def decorator(fn):
            async def _wrapper(req):
                res = await fn()
                if isinstance(res, list):
                    return types.ListToolsResult(tools=res)
                return res
            server.add_request_handler("tools/list", types.ListToolsRequest, _wrapper)
            return fn
        return decorator
    server.list_tools = _compat_list_tools

if not hasattr(server, "call_tool"):
    def _compat_call_tool():
        def decorator(fn):
            async def _wrapper(req):
                name = getattr(req.params, "name", None) or getattr(req, "name", "")
                args = getattr(req.params, "arguments", None) or getattr(req, "arguments", {})
                res = await fn(name, args)
                if isinstance(res, list):
                    return types.CallToolResult(content=res)
                return res
            server.add_request_handler("tools/call", types.CallToolRequest, _wrapper)
            return fn
        return decorator
    server.call_tool = _compat_call_tool



# -------------------------------------------------------------
# PowerShell Async Runner
# -------------------------------------------------------------
def decode_output(b: bytes) -> str:
    for encoding in ("utf-8", "cp1252", "cp850"):
        try:
            return b.decode(encoding)
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", errors="replace")


async def run_powershell_async(cmd_str: str, timeout: int = 60) -> tuple[int, str, str]:
    """Runs a PowerShell command locally via async subprocess"""
    full_cmd = f"$ProgressPreference = 'SilentlyContinue'; {cmd_str}"
    encoded_cmd = base64.b64encode(full_cmd.encode('utf-16-le')).decode('utf-8')

    powershell_exe = "powershell.exe"
    if os.name == "nt":
        system_root = os.environ.get("SystemRoot", "C:\\Windows")
        standard_path = os.path.join(system_root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
        if os.path.exists(standard_path):
            powershell_exe = standard_path

    proc = await asyncio.create_subprocess_exec(
        powershell_exe,
        "-NoProfile",
        "-NonInteractive",
        "-EncodedCommand",
        encoded_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        exit_code = proc.returncode
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except OSError:
            pass
        stdout_bytes, stderr_bytes = b"", b"Command timed out"
        exit_code = -1

    stderr_str = decode_output(stderr_bytes)
    if stderr_str.strip().startswith("#< CLIXML"):
        stderr_str = ""

    return exit_code, decode_output(stdout_bytes), stderr_str


async def run_active_powershell(session: HostSession, command: str, timeout: int = 60) -> tuple[int, str, str]:
    if not session or session.mode != "powershell":
        raise ValueError("Active session is not in PowerShell mode")

    if is_local_host(session.host):
        return await run_powershell_async(command, timeout=timeout)

    if session.username and session.password:
        ps_cmd = f"""
        $secpasswd = ConvertTo-SecureString '{ps_esc(session.password)}' -AsPlainText -Force
        $creds = New-Object System.Management.Automation.PSCredential ('{ps_esc(session.username)}', $secpasswd)
        Invoke-Command -ComputerName '{ps_esc(session.host)}' -Credential $creds -ScriptBlock {{ {command} }}
        """
    else:
        ps_cmd = f"Invoke-Command -ComputerName '{ps_esc(session.host)}' -ScriptBlock {{ {command} }}"

    return await run_powershell_async(ps_cmd, timeout=timeout)


# -------------------------------------------------------------
# MCP Tool Catalog
# -------------------------------------------------------------
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="connect",
            description="Connect to SSH server (Linux/Debian) or initialize PowerShell/WinRM target computer with automatic ~/.ssh/config resolution and Ed25519/RSA multi-key support",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": "Host IP, FQDN or ~/.ssh/config alias (e.g. '192.168.1.100', 'srv-linux')",
                    },
                    "port": {
                        "type": "integer",
                        "description": "SSH port (default: 22 or resolved from config)",
                    },
                    "username": {
                        "type": "string",
                        "description": "Username (overrides environment variable / config)",
                    },
                    "password": {
                        "type": "string",
                        "description": "Password for authentication",
                    },
                    "key_path": {
                        "type": "string",
                        "description": "Path to SSH private key (supports Ed25519, RSA, ECDSA)",
                    },
                    "key_passphrase": {
                        "type": "string",
                        "description": "Passphrase for encrypted SSH private key",
                    },
                    "mode": {
                        "type": "string",
                        "description": "Connection mode: 'ssh' (Linux/Unix) or 'powershell' (Windows Domain/WinRM)",
                        "enum": ["ssh", "powershell"],
                    },
                    "alias": {
                        "type": "string",
                        "description": "Optional session alias for multi-host management",
                    }
                },
                "required": [],
            },
        ),
        types.Tool(
            name="disconnect",
            description="Disconnect from active SSH server or reset session state",
            inputSchema={
                "type": "object",
                "properties": {
                    "alias": {"type": "string", "description": "Optional session alias to disconnect"}
                },
                "required": [],
            },
        ),
        types.Tool(
            name="execute",
            description="Execute command on active server/host with smart output truncation and dangerous command detection",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to execute (e.g. 'ls -la', 'uname -a')"},
                    "timeout": {"type": "integer", "description": "Command timeout in seconds (default: 60)"},
                    "alias": {"type": "string", "description": "Optional session alias to run on"}
                },
                "required": ["command"],
            },
        ),
        types.Tool(
            name="sudo_execute",
            description="Execute elevated command via sudo with safe password injection (SSH Linux mode)",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Privileged command to execute (without 'sudo')"},
                    "sudo_password": {"type": "string", "description": "Optional sudo password if different from connection password"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default: 60)"}
                },
                "required": ["command"],
            },
        ),
        types.Tool(
            name="read_remote_file",
            description="Read content or sliced line range of a remote file with 1-indexed line numbers (ideal for code/config inspection without downloading)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute remote file path"},
                    "start_line": {"type": "integer", "description": "Starting line number (1-indexed, default: 1)"},
                    "end_line": {"type": "integer", "description": "Ending line number (inclusive)"},
                    "max_lines": {"type": "integer", "description": "Max lines to return (default: 500)"}
                },
                "required": ["path"],
            },
        ),
        types.Tool(
            name="write_remote_file",
            description="Write or append content directly to a remote file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute remote file path"},
                    "content": {"type": "string", "description": "Content to write"},
                    "append": {"type": "boolean", "description": "Set true to append instead of overwrite"}
                },
                "required": ["path", "content"],
            },
        ),
        types.Tool(
            name="tail_remote_log",
            description="View the last N lines of any remote log file (e.g. /var/log/syslog, app.log)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to log file"},
                    "lines": {"type": "integer", "description": "Number of lines to tail (default: 50)"}
                },
                "required": ["path"],
            },
        ),
        types.Tool(
            name="docker_inspect",
            description="Inspect Docker containers, resource stats (CPU/Memory), and container logs on active Linux host",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action: 'ps' (running), 'ps_all' (all), 'stats' (live CPU/Mem), 'logs' (container logs), 'inspect'",
                        "enum": ["ps", "ps_all", "stats", "logs", "inspect"]
                    },
                    "target": {"type": "string", "description": "Container name or ID (required for 'logs' and 'inspect')"},
                    "tail": {"type": "integer", "description": "Lines of logs to fetch (default: 50)"}
                },
                "required": ["action"],
            },
        ),
        types.Tool(
            name="port_scan_diagnostic",
            description="Scan listening network ports and sockets (ss/netstat/TCP connections)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="list_sessions",
            description="List all active connection sessions in the connection pool",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="upload",
            description="Upload local file to active server/host via SFTP or Windows administrative share (C$)",
            inputSchema={
                "type": "object",
                "properties": {
                    "local_path": {"type": "string", "description": "Local file path"},
                    "remote_path": {"type": "string", "description": "Remote destination path"},
                },
                "required": ["local_path", "remote_path"],
            },
        ),
        types.Tool(
            name="download",
            description="Download file from active server/host to local machine",
            inputSchema={
                "type": "object",
                "properties": {
                    "remote_path": {"type": "string", "description": "Remote file path"},
                    "local_path": {"type": "string", "description": "Local destination path"},
                },
                "required": ["remote_path", "local_path"],
            },
        ),
        types.Tool(
            name="list_files",
            description="List files in remote directory with sizes and types",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Remote directory path"},
                },
                "required": ["path"],
            },
        ),
        types.Tool(
            name="powershell_invoke",
            description="Execute arbitrary PowerShell command locally or on a remote domain machine using Invoke-Command",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "PowerShell command or script block"},
                    "computer_name": {"type": "string", "description": "Optional target Windows computer name"},
                    "timeout": {"type": "integer", "description": "Command timeout in seconds (default: 60)"}
                },
                "required": ["command"]
            }
        ),
        types.Tool(
            name="get_system_info",
            description="Diagnose active host: gathers CPU load, memory usage, disk space, network interfaces, and OS version.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="manage_service",
            description="Manage a system service (start, stop, restart, or check status) on active host",
            inputSchema={
                "type": "object",
                "properties": {
                    "service_name": {"type": "string", "description": "Name of the system service (e.g. wuauserv, sshd, nginx)"},
                    "action": {"type": "string", "enum": ["status", "start", "stop", "restart", "enable", "disable"]},
                },
                "required": ["service_name", "action"],
            },
        ),
        types.Tool(
            name="read_event_logs",
            description="Fetch recent diagnostic system/application event logs on active host",
            inputSchema={
                "type": "object",
                "properties": {
                    "log_name": {"type": "string", "description": "Log channel (Windows: System, Application; Linux: syslog, auth)", "default": "System"},
                    "level": {"type": "string", "enum": ["Error", "Warning", "Information", "All"], "default": "All"},
                    "count": {"type": "integer", "description": "Number of log entries to retrieve (default: 10)", "default": 10},
                },
                "required": [],
            },
        )
    ]


# -------------------------------------------------------------
# Tool Execution Dispatcher
# -------------------------------------------------------------
@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    if arguments is None:
        arguments = {}

    try:
        logger.info("Tool called: %s with args: %s", name, {k: v for k, v in arguments.items() if "pass" not in k.lower()})
        
        if name == "connect":
            return await handle_connect(arguments)
        elif name == "disconnect":
            return await handle_disconnect(arguments)
        elif name == "list_sessions":
            return await handle_list_sessions()
        elif name == "execute":
            return await handle_execute(arguments)
        elif name == "sudo_execute":
            return await handle_sudo_execute(arguments)
        elif name == "read_remote_file":
            return await handle_read_remote_file(arguments)
        elif name == "write_remote_file":
            return await handle_write_remote_file(arguments)
        elif name == "tail_remote_log":
            return await handle_tail_remote_log(arguments)
        elif name == "docker_inspect":
            return await handle_docker_inspect(arguments)
        elif name == "port_scan_diagnostic":
            return await handle_port_scan_diagnostic()
        elif name == "upload":
            return await handle_upload(arguments)
        elif name == "download":
            return await handle_download(arguments)
        elif name == "list_files":
            return await handle_list_files(arguments)
        elif name == "powershell_invoke":
            return await handle_powershell_invoke(arguments)
        elif name == "get_system_info":
            return await handle_get_system_info()
        elif name == "manage_service":
            return await handle_manage_service(arguments)
        elif name == "read_event_logs":
            return await handle_read_event_logs(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        logger.error("Error executing tool '%s': %s", name, str(e))
        logger.error(traceback.format_exc())
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


# -------------------------------------------------------------
# Handlers Implementation
# -------------------------------------------------------------
async def handle_connect(arguments: Dict[str, Any]) -> list[types.TextContent]:
    host = arguments.get("host", SSH_HOST)
    port = arguments.get("port", SSH_PORT)
    username = arguments.get("username", SSH_USERNAME)
    password = arguments.get("password", SSH_PASSWORD)
    key_path = arguments.get("key_path", SSH_KEY_PATH)
    key_passphrase = arguments.get("key_passphrase", SSH_KEY_PASSPHRASE)
    mode = arguments.get("mode", CONNECTION_MODE).lower()
    alias = arguments.get("alias")

    if not host:
        raise ValueError("Host is required (e.g. '192.168.1.100' or '~/.ssh/config' alias)")

    if mode == "powershell":
        session = pool.connect_powershell(
            host=host,
            username=username,
            password=password,
            alias=alias
        )
        if not is_local_host(host):
            # Validate remote powershell connectivity
            exit_code, stdout, stderr = await run_active_powershell(session, "1", timeout=15)
            if exit_code != 0:
                pool.disconnect(session.alias)
                raise ValueError(f"Failed to connect via PowerShell to {host}: {stderr or stdout}")
        return [types.TextContent(type="text", text=f"Connected to {host} via PowerShell/WinRM (alias='{session.alias}')")]

    # SSH mode
    session = await pool.connect_ssh(
        host=host,
        port=port,
        username=username,
        password=password,
        key_path=key_path,
        key_passphrase=key_passphrase,
        alias=alias
    )
    return [types.TextContent(type="text", text=f"Connected to {session.username}@{session.host}:{session.port} via SSH (alias='{session.alias}')")]


async def handle_disconnect(arguments: Dict[str, Any]) -> list[types.TextContent]:
    alias = arguments.get("alias")
    success = pool.disconnect(alias)
    if success:
        return [types.TextContent(type="text", text=f"Disconnected session '{alias or 'default'}'")]
    return [types.TextContent(type="text", text="No active session found to disconnect")]


async def handle_list_sessions() -> list[types.TextContent]:
    sessions = pool.list_sessions()
    return [types.TextContent(type="text", text=json.dumps(sessions, indent=2))]


async def handle_execute(arguments: Dict[str, Any]) -> list[types.TextContent]:
    command = arguments.get("command")
    if not command:
        raise ValueError("Command is required")

    timeout = arguments.get("timeout", 60)
    alias = arguments.get("alias")
    session = pool.get_session(alias)

    if not session or not session.is_active():
        raise ValueError("No active connection. Please call 'connect' first.")

    # Dangerous command warning inspection
    is_danger, danger_warning = is_dangerous_command(command)
    warning_header = f"{danger_warning}\n\n" if is_danger else ""

    if session.mode == "powershell":
        exit_status, stdout_data, stderr_data = await run_active_powershell(session, command, timeout=timeout)
        result = f"{warning_header}Command: {command}\nConnection: {session.host} (PowerShell)\nExit status: {exit_status}\n\n"
        if stdout_data:
            result += f"STDOUT:\n{smart_truncate(stdout_data)}\n"
        if stderr_data:
            result += f"STDERR:\n{smart_truncate(stderr_data)}\n"
        return [types.TextContent(type="text", text=result)]

    # SSH mode
    stdin, stdout, stderr = session.ssh_client.exec_command(command, timeout=timeout)
    stdout_data = stdout.read().decode("utf-8", errors="replace")
    stderr_data = stderr.read().decode("utf-8", errors="replace")
    exit_status = stdout.channel.recv_exit_status()

    result = f"{warning_header}Command: {command}\nExit status: {exit_status}\n\n"
    if stdout_data:
        result += f"STDOUT:\n{smart_truncate(stdout_data)}\n"
    if stderr_data:
        result += f"STDERR:\n{smart_truncate(stderr_data)}\n"

    return [types.TextContent(type="text", text=result)]


async def handle_sudo_execute(arguments: Dict[str, Any]) -> list[types.TextContent]:
    command = arguments.get("command")
    sudo_password = arguments.get("sudo_password")
    timeout = arguments.get("timeout", 60)
    
    session = pool.get_session()
    if not session or session.mode != "ssh":
        raise ValueError("sudo_execute is only supported on active SSH Linux connections")

    res = await execute_sudo(session, command, sudo_password, timeout)
    return [types.TextContent(type="text", text=f"Sudo Command: {command}\nExit status: {res['exit_status']}\n\nOutput:\n{res['stdout']}")]


async def handle_read_remote_file(arguments: Dict[str, Any]) -> list[types.TextContent]:
    path = arguments.get("path")
    start_line = arguments.get("start_line", 1)
    end_line = arguments.get("end_line")
    max_lines = arguments.get("max_lines", 500)
    
    session = pool.get_session()
    if not session:
        raise ValueError("No active connection. Please call 'connect' first.")

    res = await read_remote_file_content(session, path, start_line, end_line, max_lines)
    return [types.TextContent(type="text", text=res)]


async def handle_write_remote_file(arguments: Dict[str, Any]) -> list[types.TextContent]:
    path = arguments.get("path")
    content = arguments.get("content", "")
    append = arguments.get("append", False)
    
    session = pool.get_session()
    if not session:
        raise ValueError("No active connection. Please call 'connect' first.")

    res = await write_remote_file_content(session, path, content, append)
    return [types.TextContent(type="text", text=res)]


async def handle_tail_remote_log(arguments: Dict[str, Any]) -> list[types.TextContent]:
    path = arguments.get("path")
    lines = arguments.get("lines", 50)
    
    session = pool.get_session()
    if not session:
        raise ValueError("No active connection. Please call 'connect' first.")

    res = await tail_remote_log_content(session, path, lines)
    return [types.TextContent(type="text", text=f"Log: {path} (Last {lines} lines):\n{res}")]


async def handle_docker_inspect(arguments: Dict[str, Any]) -> list[types.TextContent]:
    action = arguments.get("action", "ps")
    target = arguments.get("target")
    tail = arguments.get("tail", 50)
    
    session = pool.get_session()
    if not session:
        raise ValueError("No active connection. Please call 'connect' first.")

    res = await inspect_docker(session, action, target, tail)
    return [types.TextContent(type="text", text=res)]


async def handle_port_scan_diagnostic() -> list[types.TextContent]:
    session = pool.get_session()
    if not session:
        raise ValueError("No active connection. Please call 'connect' first.")

    res = await scan_listening_ports(session)
    return [types.TextContent(type="text", text=f"Listening Ports & Sockets on {session.host}:\n{res}")]


async def handle_upload(arguments: Dict[str, Any]) -> list[types.TextContent]:
    local_path = arguments.get("local_path")
    remote_path = arguments.get("remote_path")
    if not local_path or not remote_path:
        raise ValueError("local_path and remote_path are required")

    session = pool.get_session()
    if not session:
        raise ValueError("No active connection")

    if session.mode == "powershell":
        unc = get_unc_path(session.host, remote_path)
        import shutil
        os.makedirs(os.path.dirname(unc), exist_ok=True)
        shutil.copy2(local_path, unc)
        return [types.TextContent(type="text", text=f"Uploaded {local_path} to {remote_path} via UNC share")]

    if not session.sftp_client:
        raise ValueError("SFTP client not connected")

    session.sftp_client.put(local_path, remote_path)
    return [types.TextContent(type="text", text=f"Uploaded {local_path} to {remote_path} via SFTP")]


async def handle_download(arguments: Dict[str, Any]) -> list[types.TextContent]:
    remote_path = arguments.get("remote_path")
    local_path = arguments.get("local_path")
    if not remote_path or not local_path:
        raise ValueError("remote_path and local_path are required")

    session = pool.get_session()
    if not session:
        raise ValueError("No active connection")

    if session.mode == "powershell":
        unc = get_unc_path(session.host, remote_path)
        import shutil
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        shutil.copy2(unc, local_path)
        return [types.TextContent(type="text", text=f"Downloaded {remote_path} to {local_path} via UNC share")]

    if not session.sftp_client:
        raise ValueError("SFTP client not connected")

    session.sftp_client.get(remote_path, local_path)
    return [types.TextContent(type="text", text=f"Downloaded {remote_path} to {local_path} via SFTP")]


async def handle_list_files(arguments: Dict[str, Any]) -> list[types.TextContent]:
    path = arguments.get("path")
    if not path:
        raise ValueError("path is required")

    session = pool.get_session()
    if not session:
        raise ValueError("No active connection")

    if session.mode == "powershell":
        inner_cmd = f"Get-ChildItem -Path '{ps_esc(path)}' | Select-Object Name, Length, PSIsContainer | ConvertTo-Json -Compress"
        exit_code, stdout, stderr = await run_active_powershell(session, inner_cmd, timeout=30)
        return [types.TextContent(type="text", text=f"Files in {path} on {session.host}:\n{stdout.strip()}")]

    if not session.sftp_client:
        raise ValueError("SFTP client not connected")

    file_list = session.sftp_client.listdir(path)
    info = []
    for fn in file_list:
        try:
            stat = session.sftp_client.stat(f"{path}/{fn}")
            is_dir = stat.st_mode & 0o40000 != 0
            info.append(f"{fn} ({'directory' if is_dir else 'file'}, {stat.st_size} bytes)")
        except Exception:
            info.append(fn)

    return [types.TextContent(type="text", text=f"Files in {path}:\n" + "\n".join(info))]


async def handle_powershell_invoke(arguments: Dict[str, Any]) -> list[types.TextContent]:
    command = arguments.get("command")
    computer_name = arguments.get("computer_name")
    timeout = arguments.get("timeout", 60)

    if not command:
        raise ValueError("Command is required")

    session = pool.get_session()
    if computer_name and not is_local_host(computer_name):
        if session and session.username and session.password:
            ps_cmd = f"""
            $secpasswd = ConvertTo-SecureString '{ps_esc(session.password)}' -AsPlainText -Force
            $creds = New-Object System.Management.Automation.PSCredential ('{ps_esc(session.username)}', $secpasswd)
            Invoke-Command -ComputerName '{ps_esc(computer_name)}' -Credential $creds -ScriptBlock {{ {command} }}
            """
        else:
            ps_cmd = f"Invoke-Command -ComputerName '{ps_esc(computer_name)}' -ScriptBlock {{ {command} }}"
    else:
        ps_cmd = command

    exit_code, stdout, stderr = await run_powershell_async(ps_cmd, timeout=timeout)
    res = f"PowerShell Command: {command}\nExit status: {exit_code}\n\n"
    if stdout:
        res += f"STDOUT:\n{smart_truncate(stdout)}\n"
    if stderr:
        res += f"STDERR:\n{smart_truncate(stderr)}\n"

    return [types.TextContent(type="text", text=res)]


async def handle_get_system_info() -> list[types.TextContent]:
    session = pool.get_session()
    if not session:
        raise ValueError("No active connection")

    if session.mode == "powershell":
        diag_cmd = """
        $os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, OSArchitecture, TotalVisibleMemorySize, FreePhysicalMemory
        $cpu = Get-CimInstance Win32_Processor | Select-Object Name, LoadPercentage
        $disks = Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | Select-Object DeviceID, Size, FreeSpace
        @{
            OS = $os.Caption + " (" + $os.Version + ") " + $os.OSArchitecture
            Memory = @{ TotalGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2); FreeGB = [math]::Round($os.FreePhysicalMemory / 1MB, 2) }
            CPU = @{ Model = $cpu.Name; LoadPercent = $cpu.LoadPercentage }
            Disks = $disks | ForEach-Object { @{ Drive = $_.DeviceID; TotalGB = [math]::Round($_.Size / 1GB, 2); FreeGB = [math]::Round($_.FreeSpace / 1GB, 2) } }
        } | ConvertTo-Json -Depth 4 -Compress
        """
        exit_code, stdout, stderr = await run_active_powershell(session, diag_cmd)
        return [types.TextContent(type="text", text=f"System Diagnostics ({session.host}):\n{stdout.strip()}")]

    cmd = "echo '--- OS ---'; uname -a; echo '--- CPU ---'; top -b -n 1 | grep 'Cpu(s)' | head -n 1; echo '--- Memory ---'; free -m; echo '--- Disk ---'; df -h"
    stdin, stdout, stderr = session.ssh_client.exec_command(cmd, timeout=30)
    stdout_data = stdout.read().decode("utf-8", errors="replace")
    return [types.TextContent(type="text", text=f"System Diagnostics ({session.host}):\n{stdout_data}")]


async def handle_manage_service(arguments: Dict[str, Any]) -> list[types.TextContent]:
    service_name = arguments.get("service_name")
    action = arguments.get("action")
    if not service_name or not action:
        raise ValueError("service_name and action are required")

    session = pool.get_session()
    if not session:
        raise ValueError("No active connection")

    if session.mode == "powershell":
        if action == "status":
            cmd = f"Get-Service -Name '{ps_esc(service_name)}' | Select-Object Name, Status | ConvertTo-Json -Compress"
        else:
            cmd = f"{action.capitalize()}-Service -Name '{ps_esc(service_name)}' -PassThru | Select-Object Name, Status | ConvertTo-Json -Compress"
        exit_code, stdout, stderr = await run_active_powershell(session, cmd)
        return [types.TextContent(type="text", text=f"Service action '{action}' on '{service_name}':\n{stdout.strip()}")]

    if action == "status":
        cmd = f"systemctl status {service_name}"
    else:
        cmd = f"sudo systemctl {action} {service_name} && systemctl status {service_name}"
    stdin, stdout, stderr = session.ssh_client.exec_command(cmd, timeout=30)
    out = stdout.read().decode("utf-8", errors="replace")
    return [types.TextContent(type="text", text=f"Service Action Result:\n{out}")]


async def handle_read_event_logs(arguments: Dict[str, Any]) -> list[types.TextContent]:
    log_name = arguments.get("log_name", "System")
    level = arguments.get("level", "All")
    count = arguments.get("count", 10)
    alias = arguments.get("alias")

    session = pool.get_session(alias)
    if not session:
        raise ValueError("No active connection. Please call 'connect' first.")

    if session.mode == "powershell":
        cmd = f"Get-EventLog -LogName '{ps_esc(log_name)}' -Newest {int(count)}"
        if level != "All":
            cmd += f" -EntryType '{ps_esc(level)}'"
        cmd += " | Select-Object TimeGenerated, EntryType, Source, Message, EventID | ConvertTo-Json -Compress"
        exit_code, stdout, stderr = await run_active_powershell(session, cmd)
        return [types.TextContent(type="text", text=f"Recent log entries ({session.host}):\n{stdout or stderr}")]
    elif session.mode == "ssh":
        if not session.ssh_client:
            raise ValueError("SSH client not connected")
        if log_name.lower() in ("system", "syslog"):
            cmd = f"journalctl -n {int(count)} --no-pager 2>/dev/null || tail -n {int(count)} /var/log/syslog 2>/dev/null || tail -n {int(count)} /var/log/messages"
        elif log_name.lower() in ("auth", "security"):
            cmd = f"tail -n {int(count)} /var/log/auth.log 2>/dev/null || journalctl -u ssh -n {int(count)} --no-pager"
        else:
            cmd = f"tail -n {int(count)} /var/log/{log_name} 2>/dev/null || journalctl -u {log_name} -n {int(count)} --no-pager"
        stdin, stdout_stream, stderr_stream = session.ssh_client.exec_command(cmd, timeout=20)
        out = stdout_stream.read().decode("utf-8", errors="replace")
        return [types.TextContent(type="text", text=f"Recent log entries ({log_name} on {session.host}):\n{smart_truncate(out)}")]
    else:
        raise ValueError(f"Unsupported session mode: {session.mode}")



# -------------------------------------------------------------
# Resilient Session Monkeypatch for Client Compatibility
# -------------------------------------------------------------
from mcp.shared.session import BaseSession, RequestResponder
from mcp.types import (
    JSONRPCMessage,
    JSONRPCRequest,
    JSONRPCNotification,
    JSONRPCResponse,
    JSONRPCError,
    ErrorData,
    CancelledNotification,
)

async def _resilient_receive_loop(self) -> None:
    async with self._read_stream, self._write_stream:
        async for message in self._read_stream:
            if isinstance(message, Exception):
                await self._handle_incoming(message)
            elif isinstance(message.root, JSONRPCRequest):
                try:
                    validated_request = self._receive_request_type.model_validate(
                        message.root.model_dump(
                            by_alias=True, mode="json", exclude_none=True
                        )
                    )
                except Exception as val_err:
                    method_name = getattr(message.root, "method", "unknown")
                    if method_name == "server/discover":
                        logger.info("Handled 'server/discover' handshake successfully")
                        discover_resp = JSONRPCResponse(
                            jsonrpc="2.0",
                            id=message.root.id,
                            result={
                                "serverInfo": {
                                    "name": "ssh-connect",
                                    "version": "1.0.0"
                                },
                                "protocolVersion": "2024-11-05",
                                "capabilities": {
                                    "tools": {}
                                }
                            }
                        )
                        await self._write_stream.send(JSONRPCMessage(root=discover_resp))
                        continue

                    logger.warning(f"Unrecognized request method '{method_name}': {val_err}")
                    err_msg = JSONRPCError(
                        jsonrpc="2.0",
                        id=message.root.id,
                        error=ErrorData(
                            code=-32601,
                            message=f"Method not found: {method_name}"
                        )
                    )
                    await self._write_stream.send(JSONRPCMessage(root=err_msg))
                    continue
                responder = RequestResponder(
                    request_id=message.root.id,
                    request_meta=validated_request.root.params.meta
                    if validated_request.root.params
                    else None,
                    request=validated_request,
                    session=self,
                    on_complete=lambda r: self._in_flight.pop(r.request_id, None),
                )

                self._in_flight[responder.request_id] = responder
                await self._received_request(responder)

                if not responder._completed:  # type: ignore[reportPrivateUsage]
                    await self._handle_incoming(responder)

            elif isinstance(message.root, JSONRPCNotification):
                try:
                    notification = self._receive_notification_type.model_validate(
                        message.root.model_dump(
                            by_alias=True, mode="json", exclude_none=True
                        )
                    )
                    if isinstance(notification.root, CancelledNotification):
                        cancelled_id = notification.root.params.requestId
                        if cancelled_id in self._in_flight:
                            await self._in_flight[cancelled_id].cancel()
                    else:
                        await self._received_notification(notification)
                        await self._handle_incoming(notification)
                except Exception as e:
                    logger.warning(
                        f"Failed to validate notification: {e}. Message was: {message.root}"
                    )
            else:
                stream = self._response_streams.pop(message.root.id, None)
                if stream:
                    await stream.send(message.root)
                else:
                    await self._handle_incoming(
                        RuntimeError(
                            f"Received response with an unknown request ID: {message}"
                        )
                    )

BaseSession._receive_loop = _resilient_receive_loop


# -------------------------------------------------------------
# Main Entrypoint
# -------------------------------------------------------------
async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("stdio server initialized, entering server.run()")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="ssh-connect",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
