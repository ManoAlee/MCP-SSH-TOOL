import os
from typing import Any, Dict, Optional
import logging
import traceback
import base64
import asyncio

import mcp.server.stdio
import mcp.types as types
import paramiko
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Connection state
ssh_client: Optional[paramiko.SSHClient] = None
sftp_client: Optional[paramiko.SFTPClient] = None

# PowerShell/WinRM connection state
connection_mode: str = "ssh"
ps_host: Optional[str] = None
ps_username: Optional[str] = None
ps_password: Optional[str] = None

# Try to locate the project root and load the .env file dynamically
current_dir = os.path.dirname(os.path.abspath(__file__))
env_candidates = []

if os.environ.get("SSH_MCP_ENV"):
    env_candidates.append(os.environ.get("SSH_MCP_ENV"))

# Add potential project root locations based on typical deployments
project_root = None
roots_to_check = [
    os.path.abspath(os.path.join(current_dir, "..", "..", "..", "..")), # project root if running from server/src/ssh_connect
    os.path.abspath(os.path.join(current_dir, "..", "..", "..")),       # server/
    os.getcwd()
]

for r in roots_to_check:
    env_file = os.path.join(r, ".env")
    if os.path.exists(env_file):
        env_candidates.append(env_file)
        project_root = r
        break

# Legacy fallback on Windows
if not env_candidates and os.name == "nt":
    legacy_env = r"C:\ssh-mcp\.env"
    if os.path.exists(legacy_env):
        env_candidates.append(legacy_env)
        project_root = r"C:\ssh-mcp"

# Default project root if none was found
if not project_root:
    project_root = roots_to_check[0]

# Load the first matching .env file
if env_candidates:
    env_path = env_candidates[0]
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    # Set the environment variable if not already present in the environment
                    os.environ.setdefault(key, val)
    except Exception:
        pass

# Get configuration from environment variables
SSH_HOST = os.environ.get("SSH_HOST", "")
SSH_PORT = int(os.environ.get("SSH_PORT", "22"))
SSH_USERNAME = os.environ.get("SSH_USERNAME", "")
SSH_PASSWORD = os.environ.get("SSH_PASSWORD", "")
SSH_KEY_PATH = os.environ.get("SSH_KEY_PATH", "")
SSH_KEY_PASSPHRASE = os.environ.get("SSH_KEY_PASSPHRASE", "")
CONNECTION_MODE = os.environ.get("CONNECTION_MODE", "ssh").lower()

server = Server("ssh-connect")

# Configure logging to a file for diagnostics (append mode)
# Default log path inside project_root/logs
default_log_dir = os.path.join(project_root, "logs")
try:
    os.makedirs(default_log_dir, exist_ok=True)
except Exception:
    pass

default_log_path = os.path.join(default_log_dir, "ssh-mcp.log")
LOG_PATH = os.environ.get("SSH_MCP_LOG", default_log_path)

# Ensure LOG_PATH directory exists or fallback to home/tmp
try:
    with open(LOG_PATH, "a") as f:
        pass
except Exception:
    # Fallback to home folder ~/.ssh-mcp
    fallback_dir = os.path.join(os.path.expanduser("~"), ".ssh-mcp")
    try:
        os.makedirs(fallback_dir, exist_ok=True)
        LOG_PATH = os.path.join(fallback_dir, "ssh-mcp.log")
    except Exception:
        # Ultimate fallback to system temp dir
        import tempfile
        LOG_PATH = os.path.join(tempfile.gettempdir(), "ssh-mcp.log")

logger = logging.getLogger("ssh-connect")
if not logger.handlers:
    handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info("=== SSH-Connect & PowerShell MCP Server (logging enabled) ===")


# PowerShell utilities
def decode_output(b: bytes) -> str:
    for encoding in ("utf-8", "cp1252", "cp850"):
        try:
            return b.decode(encoding)
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", errors="replace")


async def run_powershell_async(cmd_str: str, timeout: int = 60) -> tuple[int, str, str]:
    full_cmd = f"$ProgressPreference = 'SilentlyContinue'; {cmd_str}"
    encoded_cmd = base64.b64encode(full_cmd.encode('utf-16-le')).decode('utf-8')
    
    proc = await asyncio.create_subprocess_exec(
        "powershell.exe",
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


def ps_esc(s: str) -> str:
    """Escape single quotes for PowerShell single-quoted strings"""
    return s.replace("'", "''")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="connect",
            description="Connect to SSH server or initialize PowerShell/WinRM target computer",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": "Host IP or name of target computer (overrides environment variable)",
                    },
                    "port": {
                        "type": "integer",
                        "description": "SSH port (overrides environment variable, SSH mode only)",
                    },
                    "username": {
                        "type": "string",
                        "description": "Username (overrides environment variable)",
                    },
                    "password": {
                        "type": "string",
                        "description": "Password (overrides environment variable)",
                    },
                    "key_path": {
                        "type": "string",
                        "description": "Path to SSH key file (overrides environment variable, SSH mode only)",
                    },
                    "key_passphrase": {
                        "type": "string",
                        "description": "Passphrase for SSH key (overrides environment variable, SSH mode only)",
                    },
                    "mode": {
                        "type": "string",
                        "description": "Connection mode: 'ssh' or 'powershell' (for Windows domain machines using Invoke-Command)",
                        "enum": ["ssh", "powershell"],
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="disconnect",
            description="Disconnect from active SSH server or PowerShell target host",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="execute",
            description="Execute command on active server/host",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to execute"},
                    "timeout": {
                        "type": "integer",
                        "description": "Command timeout in seconds (default: 60)",
                    },
                },
                "required": ["command"],
            },
        ),
        types.Tool(
            name="upload",
            description="Upload file to active server/host",
            inputSchema={
                "type": "object",
                "properties": {
                    "local_path": {"type": "string", "description": "Local file path"},
                    "remote_path": {
                        "type": "string",
                        "description": "Remote file path",
                    },
                },
                "required": ["local_path", "remote_path"],
            },
        ),
        types.Tool(
            name="download",
            description="Download file from active server/host",
            inputSchema={
                "type": "object",
                "properties": {
                    "remote_path": {
                        "type": "string",
                        "description": "Remote file path",
                    },
                    "local_path": {"type": "string", "description": "Local file path"},
                },
                "required": ["remote_path", "local_path"],
            },
        ),
        types.Tool(
            name="list_files",
            description="List files in directory on active server/host",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path"},
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
                    "command": {
                        "type": "string",
                        "description": "PowerShell command or script block content to execute"
                    },
                    "computer_name": {
                        "type": "string",
                        "description": "Optional target Windows computer name. If provided, runs the command on that computer using Invoke-Command."
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Command timeout in seconds (default: 60)"
                    }
                },
                "required": ["command"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    """
    global ssh_client, sftp_client

    if arguments is None:
        arguments = {}

    try:
        logger.info("Tool call requested: %s %s", name, arguments)
        if name == "connect":
            return await handle_connect(arguments)
        elif name == "disconnect":
            return await handle_disconnect()
        elif name == "execute":
            return await handle_execute(arguments)
        elif name == "upload":
            return await handle_upload(arguments)
        elif name == "download":
            return await handle_download(arguments)
        elif name == "list_files":
            return await handle_list_files(arguments)
        elif name == "powershell_invoke":
            return await handle_powershell_invoke(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        logger.error("Exception while handling tool '%s': %s", name, str(e))
        tb = traceback.format_exc()
        logger.error(tb)
        return [
            types.TextContent(
                type="text",
                text=f"Error: {str(e)}",
            )
        ]


async def handle_connect(arguments: Dict[str, Any]) -> list[types.TextContent]:
    """Connect to SSH server or initialize PowerShell remoting target"""
    global ssh_client, sftp_client
    global connection_mode, ps_host, ps_username, ps_password

    # Close existing connection if any
    if ssh_client:
        ssh_client.close()
        ssh_client = None
    if sftp_client:
        sftp_client.close()
        sftp_client = None

    connection_mode = "ssh"
    ps_host = None
    ps_username = None
    ps_password = None

    # Get connection parameters
    host = arguments.get("host", SSH_HOST)
    port = arguments.get("port", SSH_PORT)
    username = arguments.get("username", SSH_USERNAME)
    password = arguments.get("password", SSH_PASSWORD)
    key_path = arguments.get("key_path", SSH_KEY_PATH)
    key_passphrase = arguments.get("key_passphrase", SSH_KEY_PASSPHRASE)
    mode = arguments.get("mode", CONNECTION_MODE).lower()

    if not host:
        raise ValueError("Host is required")

    if mode == "powershell":
        # Initialize PowerShell remoting validation
        if username and password:
            test_cmd = f"""
            $secpasswd = ConvertTo-SecureString '{ps_esc(password)}' -AsPlainText -Force
            $creds = New-Object System.Management.Automation.PSCredential ('{ps_esc(username)}', $secpasswd)
            Invoke-Command -ComputerName '{ps_esc(host)}' -Credential $creds -ScriptBlock {{ 1 }}
            """
        else:
            test_cmd = f"Invoke-Command -ComputerName '{ps_esc(host)}' -ScriptBlock {{ 1 }}"

        logger.info("Validating PowerShell remoting to host: %s", host)
        exit_code, stdout, stderr = await run_powershell_async(test_cmd, timeout=15)
        if exit_code != 0:
            err_msg = stderr.strip() or stdout.strip() or f"Process exited with code {exit_code}"
            raise ValueError(f"Failed to connect via PowerShell to {host}: {err_msg}")

        connection_mode = "powershell"
        ps_host = host
        ps_username = username
        ps_password = password

        return [
            types.TextContent(
                type="text",
                text=f"Connected to {host} via PowerShell/WinRM (Domain authentication)",
            )
        ]

    # SSH mode fallback
    if not username:
        raise ValueError("SSH username is required")
    if not password and not key_path:
        raise ValueError("Either SSH password or key path is required")

    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        if key_path:
            key = paramiko.RSAKey.from_private_key_file(
                key_path, password=key_passphrase if key_passphrase else None
            )
            ssh_client.connect(
                hostname=host, port=port, username=username, pkey=key, timeout=10
            )
        else:
            ssh_client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=10,
            )

        sftp_client = ssh_client.open_sftp()
        connection_mode = "ssh"

        return [
            types.TextContent(
                type="text",
                text=f"Connected to {username}@{host}:{port} via SSH",
            )
        ]
    except Exception as e:
        if ssh_client:
            ssh_client.close()
            ssh_client = None
        raise ValueError(f"Failed to connect: {str(e)}")


async def handle_disconnect() -> list[types.TextContent]:
    """Disconnect from active SSH server or reset PowerShell session state"""
    global ssh_client, sftp_client
    global connection_mode, ps_host, ps_username, ps_password

    if connection_mode == "powershell":
        host = ps_host
        connection_mode = "ssh"
        ps_host = None
        ps_username = None
        ps_password = None
        return [
            types.TextContent(
                type="text",
                text=f"Disconnected from PowerShell/WinRM host {host}",
            )
        ]

    if sftp_client:
        sftp_client.close()
        sftp_client = None

    if ssh_client:
        ssh_client.close()
        ssh_client = None
        return [
            types.TextContent(
                type="text",
                text="Disconnected from SSH server",
            )
        ]
    else:
        return [
            types.TextContent(
                type="text",
                text="Not connected to any SSH server",
            )
        ]


async def handle_execute(arguments: Dict[str, Any]) -> list[types.TextContent]:
    """Execute command on active server/host"""
    global ssh_client, connection_mode, ps_host, ps_username, ps_password

    command = arguments.get("command")
    if not command:
        raise ValueError("Command is required")

    timeout = arguments.get("timeout", 60)

    if connection_mode == "powershell":
        if not ps_host:
            raise ValueError("Not connected to PowerShell host")

        if ps_username and ps_password:
            ps_cmd = f"""
            $secpasswd = ConvertTo-SecureString '{ps_esc(ps_password)}' -AsPlainText -Force
            $creds = New-Object System.Management.Automation.PSCredential ('{ps_esc(ps_username)}', $secpasswd)
            Invoke-Command -ComputerName '{ps_esc(ps_host)}' -Credential $creds -ScriptBlock {{ {command} }}
            """
        else:
            ps_cmd = f"Invoke-Command -ComputerName '{ps_esc(ps_host)}' -ScriptBlock {{ {command} }}"

        logger.info("Executing remote PowerShell command on %s: %s", ps_host, command)
        exit_status, stdout_data, stderr_data = await run_powershell_async(ps_cmd, timeout=timeout)

        result = f"Command: {command}\n"
        result += f"Connection: {ps_host} (PowerShell/WinRM)\n"
        result += f"Exit status: {exit_status}\n\n"

        if stdout_data:
            result += f"STDOUT:\n{stdout_data}\n"
        if stderr_data:
            result += f"STDERR:\n{stderr_data}\n"

        return [
            types.TextContent(
                type="text",
                text=result,
            )
        ]

    # SSH mode
    if not ssh_client:
        raise ValueError("Not connected to SSH server")

    stdin, stdout, stderr = ssh_client.exec_command(command, timeout=timeout)

    stdout_data = stdout.read().decode("utf-8")
    stderr_data = stderr.read().decode("utf-8")
    exit_status = stdout.channel.recv_exit_status()

    result = f"Command: {command}\n"
    result += f"Exit status: {exit_status}\n\n"

    if stdout_data:
        result += f"STDOUT:\n{stdout_data}\n"

    if stderr_data:
        result += f"STDERR:\n{stderr_data}\n"

    return [
        types.TextContent(
            type="text",
            text=result,
        )
    ]


async def handle_upload(arguments: Dict[str, Any]) -> list[types.TextContent]:
    """Upload file to active server/host"""
    global sftp_client, connection_mode, ps_host, ps_username, ps_password

    local_path = arguments.get("local_path")
    remote_path = arguments.get("remote_path")

    if not local_path or not remote_path:
        raise ValueError("Local and remote paths are required")

    if connection_mode == "powershell":
        if not ps_host:
            raise ValueError("Not connected to PowerShell host")

        # Copy using a PSSession and Copy-Item -ToSession
        if ps_username and ps_password:
            ps_cmd = f"""
            $secpasswd = ConvertTo-SecureString '{ps_esc(ps_password)}' -AsPlainText -Force
            $creds = New-Object System.Management.Automation.PSCredential ('{ps_esc(ps_username)}', $secpasswd)
            $session = New-PSSession -ComputerName '{ps_esc(ps_host)}' -Credential $creds
            try {{
                Copy-Item -Path '{ps_esc(local_path)}' -Destination '{ps_esc(remote_path)}' -ToSession $session -Force -ErrorAction Stop
            }} finally {{
                Remove-PSSession $session
            }}
            """
        else:
            ps_cmd = f"""
            $session = New-PSSession -ComputerName '{ps_esc(ps_host)}'
            try {{
                Copy-Item -Path '{ps_esc(local_path)}' -Destination '{ps_esc(remote_path)}' -ToSession $session -Force -ErrorAction Stop
            }} finally {{
                Remove-PSSession $session
            }}
            """

        logger.info("Uploading file via PowerShell session to %s: %s -> %s", ps_host, local_path, remote_path)
        exit_code, stdout, stderr = await run_powershell_async(ps_cmd, timeout=120)
        if exit_code != 0:
            raise ValueError(f"Failed to upload file via PowerShell: {stderr.strip() or stdout.strip()}")

        return [
            types.TextContent(
                type="text",
                text=f"Uploaded {local_path} to {remote_path} on {ps_host} via PowerShell session",
            )
        ]

    # SSH mode
    if not sftp_client:
        raise ValueError("Not connected to SSH server")

    try:
        sftp_client.put(local_path, remote_path)
        return [
            types.TextContent(
                type="text",
                text=f"Uploaded {local_path} to {remote_path}",
            )
        ]
    except Exception as e:
        raise ValueError(f"Failed to upload file: {str(e)}")


async def handle_download(arguments: Dict[str, Any]) -> list[types.TextContent]:
    """Download file from active server/host"""
    global sftp_client, connection_mode, ps_host, ps_username, ps_password

    remote_path = arguments.get("remote_path")
    local_path = arguments.get("local_path")

    if not remote_path or not local_path:
        raise ValueError("Remote and local paths are required")

    if connection_mode == "powershell":
        if not ps_host:
            raise ValueError("Not connected to PowerShell host")

        # Copy using a PSSession and Copy-Item -FromSession
        if ps_username and ps_password:
            ps_cmd = f"""
            $secpasswd = ConvertTo-SecureString '{ps_esc(ps_password)}' -AsPlainText -Force
            $creds = New-Object System.Management.Automation.PSCredential ('{ps_esc(ps_username)}', $secpasswd)
            $session = New-PSSession -ComputerName '{ps_esc(ps_host)}' -Credential $creds
            try {{
                Copy-Item -Path '{ps_esc(remote_path)}' -Destination '{ps_esc(local_path)}' -FromSession $session -Force -ErrorAction Stop
            }} finally {{
                Remove-PSSession $session
            }}
            """
        else:
            ps_cmd = f"""
            $session = New-PSSession -ComputerName '{ps_esc(ps_host)}'
            try {{
                Copy-Item -Path '{ps_esc(remote_path)}' -Destination '{ps_esc(local_path)}' -FromSession $session -Force -ErrorAction Stop
            }} finally {{
                Remove-PSSession $session
            }}
            """

        logger.info("Downloading file via PowerShell session from %s: %s -> %s", ps_host, remote_path, local_path)
        exit_code, stdout, stderr = await run_powershell_async(ps_cmd, timeout=120)
        if exit_code != 0:
            raise ValueError(f"Failed to download file via PowerShell: {stderr.strip() or stdout.strip()}")

        return [
            types.TextContent(
                type="text",
                text=f"Downloaded {remote_path} to {local_path} from {ps_host} via PowerShell session",
            )
        ]

    # SSH mode
    if not sftp_client:
        raise ValueError("Not connected to SSH server")

    try:
        sftp_client.get(remote_path, local_path)
        return [
            types.TextContent(
                type="text",
                text=f"Downloaded {remote_path} to {local_path}",
            )
        ]
    except Exception as e:
        raise ValueError(f"Failed to download file: {str(e)}")


async def handle_list_files(arguments: Dict[str, Any]) -> list[types.TextContent]:
    """List files in directory on active server/host"""
    global sftp_client, connection_mode, ps_host, ps_username, ps_password

    path = arguments.get("path")
    if not path:
        raise ValueError("Path is required")

    if connection_mode == "powershell":
        if not ps_host:
            raise ValueError("Not connected to PowerShell host")

        # Get list of files structured as JSON
        inner_cmd = f"Get-ChildItem -Path '{ps_esc(path)}' | Select-Object Name, Length, PSIsContainer | ConvertTo-Json -Compress"
        
        if ps_username and ps_password:
            ps_cmd = f"""
            $secpasswd = ConvertTo-SecureString '{ps_esc(ps_password)}' -AsPlainText -Force
            $creds = New-Object System.Management.Automation.PSCredential ('{ps_esc(ps_username)}', $secpasswd)
            Invoke-Command -ComputerName '{ps_esc(ps_host)}' -Credential $creds -ScriptBlock {{ {inner_cmd} }}
            """
        else:
            ps_cmd = f"Invoke-Command -ComputerName '{ps_esc(ps_host)}' -ScriptBlock {{ {inner_cmd} }}"

        logger.info("Listing remote files on %s for path: %s", ps_host, path)
        exit_code, stdout, stderr = await run_powershell_async(ps_cmd, timeout=30)
        
        if exit_code != 0:
            raise ValueError(f"Failed to list files: {stderr.strip() or stdout.strip()}")

        file_info = []
        stdout_clean = stdout.strip()
        if stdout_clean:
            try:
                import json
                raw_data = json.loads(stdout_clean)
                items = raw_data if isinstance(raw_data, list) else [raw_data]
                
                for item in items:
                    name = item.get("Name", "")
                    is_dir = item.get("PSIsContainer", False)
                    size = item.get("Length", 0)
                    
                    if is_dir or size is None:
                        file_info.append(f"{name} (directory)")
                    else:
                        file_info.append(f"{name} (file, {size} bytes)")
            except Exception as e:
                # Fallback to plain text output if JSON parsing failed
                file_info = [stdout_clean]

        result = f"Files in {path} on {ps_host}:\n" + "\n".join(file_info)
        return [
            types.TextContent(
                type="text",
                text=result,
            )
        ]

    # SSH mode
    if not sftp_client:
        raise ValueError("Not connected to SSH server")

    try:
        file_list = sftp_client.listdir(path)
        file_info = []

        for filename in file_list:
            full_path = f"{path}/{filename}"
            try:
                stat = sftp_client.stat(full_path)
                is_dir = stat.st_mode & 0o40000 != 0  # Check if it's a directory
                size = stat.st_size
                file_type = "directory" if is_dir else "file"
                file_info.append(f"{filename} ({file_type}, {size} bytes)")
            except:
                file_info.append(f"{filename}")

        result = f"Files in {path}:\n" + "\n".join(file_info)
        return [
            types.TextContent(
                type="text",
                text=result,
            )
        ]
    except Exception as e:
        raise ValueError(f"Failed to list files: {str(e)}")


async def handle_powershell_invoke(arguments: Dict[str, Any]) -> list[types.TextContent]:
    """Execute PowerShell command locally or remotely"""
    global ps_host, ps_username, ps_password

    command = arguments.get("command")
    computer_name = arguments.get("computer_name")
    timeout = arguments.get("timeout", 60)

    if not command:
        raise ValueError("PowerShell command is required")

    # If computer_name is specified, wrap inside Invoke-Command
    if computer_name:
        # Check if we should use active connection's credentials
        if computer_name == ps_host and ps_username and ps_password:
            ps_cmd = f"""
            $secpasswd = ConvertTo-SecureString '{ps_esc(ps_password)}' -AsPlainText -Force
            $creds = New-Object System.Management.Automation.PSCredential ('{ps_esc(ps_username)}', $secpasswd)
            Invoke-Command -ComputerName '{ps_esc(computer_name)}' -Credential $creds -ScriptBlock {{ {command} }}
            """
        else:
            ps_cmd = f"Invoke-Command -ComputerName '{ps_esc(computer_name)}' -ScriptBlock {{ {command} }}"
    else:
        ps_cmd = command

    logger.info("Executing powershell_invoke (computer_name=%s): %s", computer_name, command)
    exit_code, stdout, stderr = await run_powershell_async(ps_cmd, timeout=timeout)

    result = f"PowerShell Command: {command}\n"
    if computer_name:
        result += f"Target Computer: {computer_name}\n"
    result += f"Exit status: {exit_code}\n\n"

    if stdout:
        result += f"STDOUT:\n{stdout}\n"
    if stderr:
        result += f"STDERR:\n{stderr}\n"

    return [
        types.TextContent(
            type="text",
            text=result,
        )
    ]


async def main():
    # Run the server using stdin/stdout streams
    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            logger.info("stdio server initialized, entering server.run()")
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="ssh-connect",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    except Exception as e:
        logger.error("Unhandled exception in main: %s", str(e))
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
