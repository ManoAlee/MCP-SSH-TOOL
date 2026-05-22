#!/usr/bin/env python3
"""Test SSH MCP connection via uv and JSON-RPC protocol"""
import json
import subprocess
import sys
import os

def test_mcp_server():
    """Test MCP server by sending a connect request"""
    
    # Prepare environment
    env = os.environ.copy()
    
    # Load .env variables manually for testing if present
    env_path = r'C:\ssh-mcp\.env'
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    env.setdefault(k.strip(), v.strip().strip('\'"'))
                    
    env['Path'] = "C:\\Users\\<YOUR_USER>\\.local\\bin;" + env.get('Path', '')
    
    # Create a simple JSON-RPC message to initialize the server
    init_message = {
        "jsonrpc": "2.0",
        "id": 1,
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
    
    print("Testing SSH MCP Server Connection...")
    print("=" * 50)
    
    try:
        # Start the server
        process = subprocess.Popen(
            [r"C:\ssh-mcp\server\.venv\Scripts\ssh-connect.exe"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        # Send initialize message
        process.stdin.write(json.dumps(init_message) + "\n")
        process.stdin.flush()
        
        # Read the response
        response_line = process.stdout.readline()
        
        if response_line:
            print("[OK] Server started and responded successfully!")
            print(f"\nResponse: {response_line.strip()}")
            process.terminate()
            return True
        else:
            # Try to read stderr if stdout is empty
            stderr_info = []
            try:
                # Set process stderr to non-blocking or read a bit
                import select
                # On Windows we can't use select on pipes easily, so we just try to read a line
                stderr_line = process.stderr.readline()
                if stderr_line:
                    stderr_info.append(stderr_line)
            except Exception:
                pass
            print("[FAIL] Server failed to respond.")
            if stderr_info:
                print(f"Error output: {''.join(stderr_info)}")
            process.terminate()
            return False
            
    except Exception as e:
        if 'process' in locals():
            process.kill()
        print(f"[FAIL] Test failed: {str(e)}")
        return False

if __name__ == '__main__':
    success = test_mcp_server()
    sys.exit(0 if success else 1)

