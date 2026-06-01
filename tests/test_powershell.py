#!/usr/bin/env python3
"""Test suite for PowerShell/WinRM execution mechanics in MCP server"""
import asyncio
import base64
import json
import os
import sys
import unittest

# Setup path dynamically to import the module
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, os.path.join(project_root, "server", "src"))

from ssh_connect import server

def decode_output(b: bytes) -> str:
    for encoding in ("utf-8", "cp1252", "cp850"):
        try:
            return b.decode(encoding)
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", errors="replace")

async def run_powershell_async(cmd_str: str, timeout: int = 30) -> tuple[int, str, str]:
    # Suppress progress messages globally within the script
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
    # Filter out CLIXML progress objects if they still appear
    if stderr_str.strip().startswith("#< CLIXML"):
        stderr_str = ""
        
    return exit_code, decode_output(stdout_bytes), stderr_str


class TestPowerShellMechanics(unittest.TestCase):
    def setUp(self):
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

    def test_run_powershell_basic(self):
        """Test simple local PowerShell execution via encoded command"""
        cmd = "Write-Output 'Hello from PowerShell'"
        exit_code, stdout, stderr = self.loop.run_until_complete(run_powershell_async(cmd))
        
        self.assertEqual(exit_code, 0)
        self.assertIn("Hello from PowerShell", stdout)
        self.assertEqual(stderr.strip(), "")

    def test_run_powershell_json(self):
        """Test PowerShell object to JSON serialization and parsing"""
        cmd = "@( @{Name='test.txt'; Length=1024; PSIsContainer=$false} ) | ConvertTo-Json -Compress"
        exit_code, stdout, stderr = self.loop.run_until_complete(run_powershell_async(cmd))
        
        self.assertEqual(exit_code, 0)
        data = json.loads(stdout.strip())
        if isinstance(data, list):
            item = data[0]
        else:
            item = data
        self.assertEqual(item["Name"], "test.txt")
        self.assertEqual(item["Length"], 1024)
        self.assertFalse(item["PSIsContainer"])

    def test_ps_string_escaping(self):
        """Verify PowerShell single quote escaping mechanism"""
        original = "D:\\SoMachine Software\\'Configuration'"
        escaped = original.replace("'", "''")
        self.assertEqual(escaped, "D:\\SoMachine Software\\''Configuration''")

    def test_handle_powershell_invoke_local(self):
        """Test handle_powershell_invoke locally without computer_name"""
        args = {"command": "Write-Output 'Direct Handler Test'"}
        result = self.loop.run_until_complete(server.handle_powershell_invoke(args))
        
        self.assertEqual(len(result), 1)
        self.assertIn("Direct Handler Test", result[0].text)
        self.assertIn("Exit status: 0", result[0].text)

    def test_handle_connect_invalid_host(self):
        """Test handle_connect with a fake host to verify failure handling"""
        args = {"host": "fake-host-nonexistent-12345", "mode": "powershell"}
        with self.assertRaises(ValueError) as ctx:
            self.loop.run_until_complete(server.handle_connect(args))
        self.assertIn("fake-host-nonexistent-12345", str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
