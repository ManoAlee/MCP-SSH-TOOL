# Script PowerShell para iniciar o servidor MCP SSH-Connect automaticamente
# Este script sera executado na inicializacao do sistema

param(
    [switch]$LogOnly = $false
)

# Configuracoes
$SERVER_PATH = "C:\ssh-mcp\server"
$UV_BIN = "C:\Users\<YOUR_USER>\.local\bin"
$LOG_FILE = "C:\ssh-mcp\logs\ssh-mcp.log"
$PID_FILE = "C:\ssh-mcp\logs\ssh-mcp.pid"

# Criar pasta de logs se nao existir
$logDir = Split-Path $LOG_FILE -Parent
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

# Funcao para log
function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $Message" | Tee-Object -FilePath $LOG_FILE -Append
}

# Verificar se o servidor ja esta rodando
function Is-ServerRunning {
    if (Test-Path $PID_FILE) {
        $oldPid = Get-Content $PID_FILE
        try {
            $process = Get-Process -Id $oldPid -ErrorAction Stop
            if ($process.ProcessName -like "*uv*" -or $process.ProcessName -like "*python*") {
                return $true
            }
        } catch {
            Remove-Item $PID_FILE -Force -ErrorAction SilentlyContinue
        }
    }
    return $false
}

# Adicionar uv ao PATH
if ($env:Path -notlike "*$UV_BIN*") {
    $env:Path = "$UV_BIN;$env:Path"
}

Write-Log "===== SSH-Connect MCP Server Startup ====="
Write-Log "Server path: $SERVER_PATH"
Write-Log "UV binary path: $UV_BIN"

# Verificar se o diretorio do servidor existe
if (-not (Test-Path $SERVER_PATH)) {
    Write-Log "ERROR: Server directory not found: $SERVER_PATH"
    exit 1
}

# Verificar se uv esta disponivel
$uvPath = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvPath) {
    Write-Log "ERROR: uv command not found in PATH"
    Write-Log "Trying to add uv to PATH: $UV_BIN"
    $env:Path = "$UV_BIN;$env:Path"
    
    $uvPath = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uvPath) {
        Write-Log "ERROR: uv still not found after adding to PATH"
        exit 1
    }
}

Write-Log "uv found at: $($uvPath.Source)"

# Verificar se o servidor ja esta rodando
if (Is-ServerRunning) {
    Write-Log "Server is already running (PID: $(Get-Content $PID_FILE))"
    exit 0
}

# Iniciar o servidor
Write-Log "Starting SSH-Connect MCP Server..."

try {
    Push-Location $SERVER_PATH
    
    # Iniciar o processo em background
    $process = Start-Process -FilePath "uv" `
        -ArgumentList "run", "ssh-connect" `
        -WindowStyle Hidden `
        -PassThru `
        -NoNewWindow `
        -ErrorAction Stop
    
    # Salvar o PID
    $process.Id | Out-File -FilePath $PID_FILE -Force
    
    Write-Log "Server started successfully with PID: $($process.Id)"
    Write-Log "Log file: $LOG_FILE"
    Write-Log "===== Startup Complete ====="
    
    Pop-Location
    exit 0
    
} catch {
    Write-Log "ERROR: Failed to start server: $_"
    Pop-Location
    exit 1
}

