#!/usr/bin/env python3
"""Test SSH MCP connection directly calling handlers"""
import os
import sys
import asyncio

# Setup path for reorganised structure
sys.path.insert(0, r'C:\ssh-mcp\server\src')

# Load .env variables manually for testing if present
env_path = r'C:\ssh-mcp\.env'
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('\'"'))

from ssh_connect import server

async def test_connection():
    """Test SSH connection through handler"""
    print("Testing connection directly via server module...")
    
    # Ensure variables exist
    if not os.environ.get('SSH_HOST'):
        print("[FAIL] Error: SSH_HOST environment variable not set in env or .env file.")
        return False
        
    try:
        # Test connect
        result = await server.handle_connect({})
        print("[OK] Connection test successful!")
        print(f"Result: {result[0].text}")
        
        # Test disconnect
        result = await server.handle_disconnect()
        print(f"[OK] Disconnect: {result[0].text}")
        return True
    except Exception as e:
        print(f"[FAIL] Connection failed: {str(e)}")
        return False

if __name__ == '__main__':
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)
