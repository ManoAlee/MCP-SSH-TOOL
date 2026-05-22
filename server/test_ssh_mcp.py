#!/usr/bin/env python3
"""
Test script for SSH MCP server.

This script demonstrates how to use the SSH MCP server directly from Python,
without using Cline. It performs a series of operations:
1. Connect to the SSH server
2. Execute a command
3. Upload a file
4. List files
5. Download a file
6. Disconnect from the SSH server
"""

import json
import os
import subprocess
import sys
import tempfile
import shutil

class MCPServerRunner:
    def __init__(self):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Load environment variables from .env to pass to the subprocess
        self.env = os.environ.copy()
        env_candidates = [
            os.path.join(project_root, ".env"),
            os.path.join(os.getcwd(), ".env")
        ]
        if os.name == 'nt':
            env_candidates.append(r'C:\ssh-mcp\.env')
            
        env_path = None
        for path in env_candidates:
            if os.path.exists(path):
                env_path = path
                break
                
        if env_path:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        self.env.setdefault(k.strip(), v.strip().strip('\'"'))

        if shutil.which("uv"):
            cmd = [
                "uv",
                "--directory",
                project_root,
                "run",
                "ssh-connect"
            ]
        else:
            server_py = os.path.join(project_root, "server", "src", "ssh_connect", "server.py")
            cmd = [
                sys.executable,
                server_py
            ]
            
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.env
        )
        self.msg_id = 1
        
        # Initialize the MCP session
        init_message = {
            "jsonrpc": "2.0",
            "id": self.msg_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0"
                }
            }
        }
        self._send_raw(init_message)
        # Read and ignore initialization response
        self._read_raw()
        
    def _send_raw(self, msg):
        self.process.stdin.write(json.dumps(msg) + "\n")
        self.process.stdin.flush()
        
    def _read_raw(self):
        return self.process.stdout.readline()

    def call_tool(self, tool_name, arguments=None):
        """Call an MCP tool and return the result."""
        if arguments is None:
            arguments = {}
        
        self.msg_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.msg_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        self._send_raw(request)
        response_line = self._read_raw()
        
        if not response_line:
            # Check stderr
            stderr_line = self.process.stderr.readline()
            if stderr_line:
                print(f"Error from server stderr: {stderr_line.strip()}")
            return None
            
        try:
            response = json.loads(response_line)
            if "error" in response:
                print(f"Error: {response['error']['message']}")
                return None
            return response["result"]["content"][0]["text"]
        except Exception as e:
            print(f"Failed to parse response: {e}")
            print(f"Response line: {response_line.strip()}")
            return None

    def close(self):
        self.process.terminate()
        self.process.wait()

def create_test_file():
    """Create a test file for upload."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("This is a test file for SSH MCP server testing.")
        return f.name

def main():
    """Run the SSH MCP server test."""
    print("SSH MCP Server Test")
    print("==================")
    
    runner = MCPServerRunner()
    
    try:
        # 1. Connect to SSH server
        print("\n1. Connecting to SSH server...")
        result = runner.call_tool("connect")
        print(result)
        
        # 2. Execute a command
        print("\n2. Executing command 'ls -la'...")
        result = runner.call_tool("execute", {"command": "ls -la"})
        print(result)
        
        # 3. Create and upload a test file
        print("\n3. Creating test file...")
        local_file = create_test_file()
        print(f"Test file created: {local_file}")
        
        print("\n4. Uploading test file...")
        result = runner.call_tool("upload", {
            "local_path": local_file,
            "remote_path": "test_file_mcp_test.txt"
        })
        print(result)
        
        # 4. List files to verify upload
        print("\n5. Listing files in remote home directory...")
        result = runner.call_tool("list_files", {"path": "."})
        print(result)
        
        # 5. Download the file to a different location
        download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloaded_test_file.txt")
        print(f"\n6. Downloading file to {download_path}...")
        result = runner.call_tool("download", {
            "remote_path": "test_file_mcp_test.txt",
            "local_path": download_path
        })
        print(result)
        
        # 6. Disconnect from SSH server
        print("\n7. Disconnecting from SSH server...")
        result = runner.call_tool("disconnect")
        print(result)
        
        # Clean up
        os.unlink(local_file)
        if os.path.exists(download_path):
            os.unlink(download_path)
            
        print(f"\nTest completed. Downloaded file was verified and cleaned up.")
    finally:
        runner.close()

if __name__ == "__main__":
    main()
