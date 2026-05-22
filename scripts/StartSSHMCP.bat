@echo off
REM Script para iniciar o servidor MCP SSH-Connect
REM Este arquivo sera chamado na inicializacao do Windows via Startup folder

setlocal enabledelayedexpansion

REM Configurações
set SERVER_PATH=C:\ssh-mcp\server
set UV_BIN=C:\Users\alessandro.meneses.Automotion\.local\bin
set LOG_FILE=C:\ssh-mcp\logs\ssh-mcp.log
set PID_FILE=C:\ssh-mcp\logs\ssh-mcp.pid

REM Criar pasta de logs se nao existir
if not exist "C:\ssh-mcp\logs" mkdir "C:\ssh-mcp\logs"

REM Adicionar data e hora ao log
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a:%%b)

echo [%mydate% %mytime%] === SSH-Connect MCP Server Startup === >> "%LOG_FILE%"

REM Adicionar uv ao PATH
set PATH=%UV_BIN%;%PATH%

REM Verificar se o diretório existe
if not exist "%SERVER_PATH%" (
    echo [%mydate% %mytime%] ERROR: Server directory not found: %SERVER_PATH% >> "%LOG_FILE%"
    exit /b 1
)

REM Verificar se uv está disponível
where /q uv
if errorlevel 1 (
    echo [%mydate% %mytime%] ERROR: uv command not found >> "%LOG_FILE%"
    exit /b 1
)

echo [%mydate% %mytime%] uv found, starting server... >> "%LOG_FILE%"

REM Navegar para o diretório do servidor
cd /d "%SERVER_PATH%"

REM Iniciar o servidor em background
start "" /B uv run ssh-connect

echo [%mydate% %mytime%] Server started successfully >> "%LOG_FILE%"

exit /b 0
