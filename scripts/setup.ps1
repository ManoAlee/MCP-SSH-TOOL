# Script Orquestrador de Transicao - ReorganizaÃ§Ã£o Enterprise (SSH-Connect)
# Uso: Run inside an Administrator PowerShell console:
#      .\setup.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== INICIANDO REORGANIZACAO ENTERPRISE - SSH-CONNECT ===" -ForegroundColor Cyan

# 1. Parar processos ativos que possam bloquear os arquivos do servidor
Write-Host "`n[Passo 1] Encerrando instancias ativas do Servidor SSH-MCP para evitar locks..." -ForegroundColor Yellow
try {
    # Procura processos python rodando com o nosso servidor ou uv rodando na pasta
    $activeProcesses = Get-CimInstance Win32_Process | Where-Object { 
        ($_.Name -eq "python.exe" -or $_.Name -eq "uv.exe") -and 
        ($_.CommandLine -like "*ssh-mcp*" -or $_.CommandLine -like "*ssh-connect*" -or $_.ExecutablePath -like "*C:\ssh-mcp*") 
    }
    if ($activeProcesses) {
        Write-Host "Encerrando $($activeProcesses.Count) processos..." -ForegroundColor Yellow
        foreach ($p in $activeProcesses) {
            try {
                Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
                Write-Host "  Encerrado Processo ID: $($p.ProcessId) ($($p.Name))" -ForegroundColor Gray
            } catch {}
        }
        Start-Sleep -Seconds 2
        Write-Host "Processos encerrados com sucesso." -ForegroundColor Green
    } else {
        Write-Host "Nenhum processo concorrente encontrado." -ForegroundColor Gray
    }
} catch {
    Write-Host "Aviso ao tentar encerrar processos: $_" -ForegroundColor Yellow
}

# 2. Criar Estrutura de Pastas
Write-Host "`n[Passo 2] Criando a nova estrutura de diretorios..." -ForegroundColor Yellow
$dirs = @(
    "C:\ssh-mcp\config",
    "C:\ssh-mcp\docs",
    "C:\ssh-mcp\logs",
    "C:\ssh-mcp\scripts",
    "C:\ssh-mcp\tests"
)
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  [OK] Criado: $dir" -ForegroundColor Green
    } else {
        Write-Host "  [OK] Ja existe: $dir" -ForegroundColor Gray
    }
}

# 3. Renomear pasta do Servidor
Write-Host "`n[Passo 3] Renomeando pasta do servidor Python..." -ForegroundColor Yellow
$oldServerDir = "C:\ssh-mcp\ssh-connect-mcp-server"
$newServerDir = "C:\ssh-mcp\server"

if (Test-Path $oldServerDir) {
    if (Test-Path $newServerDir) {
        Write-Host "Pasta de destino '$newServerDir' ja existe. Removendo versao anterior para fusao..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $newServerDir
    }
    Rename-Item -Path $oldServerDir -NewName "server" -Force
    Write-Host "  [OK] Renomeado: $oldServerDir -> $newServerDir" -ForegroundColor Green
} elseif (Test-Path $newServerDir) {
    Write-Host "  [OK] Servidor ja esta na pasta correta: $newServerDir" -ForegroundColor Gray
} else {
    Write-Host "ERRO: Diretorio do servidor nao encontrado em $oldServerDir ou $newServerDir" -ForegroundColor Red
    exit 1
}

# 4. Mover arquivos de DocumentaÃ§Ã£o
Write-Host "`n[Passo 4] Organizando documentacao..." -ForegroundColor Yellow
$docsFiles = @(
    "CHECKLIST_OPERACAO.md",
    "DOCUMENTACAO_COMPLETA.md",
    "GUIA_CONFIGURACAO_TROUBLESHOOTING.md",
    "INDICE_DOCUMENTACAO.md",
    "SETUP_COMPLETE.md",
    "VALIDATION_REPORT.md",
    "VALIDATION_SUMMARY.md"
)
foreach ($file in $docsFiles) {
    $srcPath = "C:\ssh-mcp\$file"
    if (Test-Path $srcPath) {
        Move-Item -Path $srcPath -Destination "C:\ssh-mcp\docs\" -Force
        Write-Host "  [OK] Movido: $file -> docs/" -ForegroundColor Green
    }
}

# 5. Mover arquivos de ConfiguraÃ§Ã£o
Write-Host "`n[Passo 5] Organizando arquivos de configuracao..." -ForegroundColor Yellow
$configFiles = @(
    "mcp_config_error_fix.json",
    "mcp_config_qwen_npx.json",
    "mcp_config_qwen_uvx.json",
    "mcp_config_qwen_uvx_full.json",
    "mcp_config_test.json"
)
foreach ($file in $configFiles) {
    $srcPath = "C:\ssh-mcp\$file"
    if (Test-Path $srcPath) {
        Move-Item -Path $srcPath -Destination "C:\ssh-mcp\config\" -Force
        Write-Host "  [OK] Movido: $file -> config/" -ForegroundColor Green
    }
}

# 6. Remover arquivos legados na raiz que agora estao sob scripts/ e tests/
Write-Host "`n[Passo 6] Limpando scripts e testes antigos da raiz..." -ForegroundColor Yellow
$rootLegacyFiles = @(
    "Register-StartupTask.ps1",
    "Start-SSHMCPServer.ps1",
    "StartSSHMCP.bat",
    "quick-check.ps1",
    "start_ssh_mcp.bat",
    "test_mcp.py",
    "test_mcp_server.py",
    "test_ssh_direct.py"
)
foreach ($file in $rootLegacyFiles) {
    $srcPath = "C:\ssh-mcp\$file"
    if (Test-Path $srcPath) {
        Remove-Item -Path $srcPath -Force
        Write-Host "  [OK] Removido arquivo raiz legado: $file" -ForegroundColor Green
    }
}

# Mover logs existentes se houver na raiz
$logFiles = @("server_run.log", "ssh-mcp.log", "startup.log")
foreach ($log in $logFiles) {
    $srcPath = "C:\ssh-mcp\$log"
    if (Test-Path $srcPath) {
        Move-Item -Path $srcPath -Destination "C:\ssh-mcp\logs\" -Force
        Write-Host "  [OK] Movido log: $log -> logs/" -ForegroundColor Green
    }
}

# 7. Recriar Ambiente Virtual Python (.venv)
Write-Host "`n[Passo 7] Recriando ambiente virtual Python (.venv) no novo caminho..." -ForegroundColor Yellow
$venvDir = "C:\ssh-mcp\server\.venv"
$uvPath = "C:\Users\<YOUR_USER>\.local\bin\uv.exe"

# Adicionar uv ao PATH desta sessao
$env:Path = "C:\Users\<YOUR_USER>\.local\bin;" + $env:Path

if (Test-Path $venvDir) {
    Write-Host "Removendo .venv antigo..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $venvDir
}

Write-Host "Inicializando novo venv usando uv..." -ForegroundColor Yellow
Push-Location "C:\ssh-mcp\server"
& $uvPath venv
Write-Host "Instalando o pacote do servidor e dependencias no modo editavel (-e .)..." -ForegroundColor Yellow
& $uvPath pip install -e .
Pop-Location
Write-Host "  [OK] Ambiente virtual rebuilded com sucesso!" -ForegroundColor Green

# 8. Aplicar Configuracoes nos Clientes
Write-Host "`n[Passo 8] Instalando configuracoes nos clientes (Gemini/Antigravity)..." -ForegroundColor Yellow
if (Test-Path "C:\ssh-mcp\scripts\install_mcp_config.ps1") {
    & "C:\ssh-mcp\scripts\install_mcp_config.ps1"
    Write-Host "  [OK] Configuracoes aplicadas!" -ForegroundColor Green
} else {
    Write-Host "Aviso: install_mcp_config.ps1 nao encontrado." -ForegroundColor Yellow
}

# 9. Atualizar Tarefa Agendada no Windows
Write-Host "`n[Passo 9] Atualizando tarefa agendada do Windows..." -ForegroundColor Yellow
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin) {
    if (Test-Path "C:\ssh-mcp\scripts\Register-StartupTask.ps1") {
        & "C:\ssh-mcp\scripts\Register-StartupTask.ps1"
        Write-Host "  [OK] Tarefa agendada atualizada!" -ForegroundColor Green
    } else {
        Write-Host "Aviso: Register-StartupTask.ps1 nao encontrado." -ForegroundColor Yellow
    }
} else {
    Write-Host "Aviso: Nao executando como Administrator. Pulando atualizacao da tarefa do Windows." -ForegroundColor Yellow
}

# 10. Executar Suite de Diagnostico
Write-Host "`n[Passo 10] Executando suite de testes de integridade..." -ForegroundColor Yellow
if (Test-Path "C:\ssh-mcp\scripts\quick-check.ps1") {
    & "C:\ssh-mcp\scripts\quick-check.ps1"
} else {
    Write-Host "Aviso: quick-check.ps1 nao encontrado." -ForegroundColor Yellow
}

Write-Host "`n=== PROCESSO DE REORGANIZACAO ENTERPRISE CONCLUIDO COM SUCESSO ===" -ForegroundColor Green

