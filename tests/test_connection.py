#!/usr/bin/env python3
"""Test SSH connection directly with paramiko"""
import paramiko
import sys
import os

def test_ssh_connection():
    """Test SSH connection"""
    
    # Load .env variables manually for testing if present
    # Determine project root dynamically (tests/ is under the root)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, ".."))
    
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

    host = ''
    port = 22
    username = ''
    password = ''
    
    if env_path:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    k = k.strip()
                    v = v.strip().strip('\'"')
                    if k == 'SSH_HOST': host = v
                    elif k == 'SSH_PORT': port = int(v)
                    elif k == 'SSH_USERNAME': username = v
                    elif k == 'SSH_PASSWORD': password = v

    if not host or not username:
        print(f"[FAIL] SSH_HOST or SSH_USERNAME not found in environment or .env file (searched: {env_candidates})")
        return False

    print(f"Testing SSH Connection to {host}:{port}...")
    print("=" * 50)
    
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Attempt to connect
        ssh_client.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=10,
            allow_agent=False,
            look_for_keys=False
        )
        
        print("[OK] SSH Connection successful!")
        
        # Test a simple command
        stdin, stdout, stderr = ssh_client.exec_command('whoami')
        result = stdout.read().decode().strip()
        print(f"[OK] Command executed: whoami -> {result}")
        
        # Close connection
        ssh_client.close()
        print("[OK] Disconnected successfully")
        
        return True
        
    except paramiko.AuthenticationException as e:
        print(f"[FAIL] Authentication failed: {str(e)}")
        return False
    except paramiko.SSHException as e:
        print(f"[FAIL] SSH error: {str(e)}")
        return False
    except Exception as e:
        print(f"[FAIL] Connection failed: {str(e)}")
        return False

if __name__ == '__main__':
    success = test_ssh_connection()
    sys.exit(0 if success else 1)
