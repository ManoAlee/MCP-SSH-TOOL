@echo off
REM Script para iniciar o servidor MCP SSH-Connect automaticamente

REM Adicionar uv ao PATH
set PATH=C:\Users\<YOUR_USER>\.local\bin;%PATH%

REM Criar pasta de logs se nao existir
if not exist "C:\ssh-mcp\logs" mkdir "C:\ssh-mcp\logs"

REM Navegar atÃ© o diretÃ³rio do servidor
cd /d C:\ssh-mcp\server

REM Iniciar o servidor em background
start "" uv run ssh-connect

REM Log de inicializaÃ§Ã£o
echo [%date% %time%] SSH-Connect server started >> C:\ssh-mcp\logs\startup.log

exit /b 0

