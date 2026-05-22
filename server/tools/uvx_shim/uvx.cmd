@echo off
rem uvx shim for ssh-connect MCP server
set LOG=C:\ssh-mcp\uvx-shim.log
echo [%DATE% %TIME%] uvx shim started args: %* >> "%LOG%"
echo PATH: %PATH% >> "%LOG%"
rem Launch the installed ssh-connect server using the repo venv python (unbuffered)
"C:\ssh-mcp\ssh-connect-mcp-server\.venv\Scripts\python.exe" -u -m ssh_connect %*
