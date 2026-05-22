# Script para registrar a tarefa agendada do Windows
# Execute este script uma vez como Administrator

$taskName = "SSH-Connect MCP Server"
$taskDescription = "Inicia o servidor MCP SSH-Connect na inicialização do sistema"
$scriptPath = "C:\ssh-mcp\scripts\Start-SSHMCPServer.ps1"
$user = "NT AUTHORITY\SYSTEM"

# Verificar se esta executando como Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: Este script precisa ser executado como Administrator!" -ForegroundColor Red
    Write-Host "Por favor, abra o PowerShell como Administrator e execute novamente." -ForegroundColor Yellow
    exit 1
}

Write-Host "Registrando tarefa agendada: $taskName" -ForegroundColor Green

# Remover tarefa existente se houver
try {
    $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "Removendo tarefa existente..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }
} catch {
    # Ignorar erros se a tarefa nao existir
}

# Criar acao da tarefa
$action = New-ScheduledTaskAction `
    -Execute "PowerShell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`""

# Criar gatilho para inicializacao do sistema
$trigger = New-ScheduledTaskTrigger -AtStartup

# Criar configurações da tarefa
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew

# Registrar a tarefa
try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -User $user `
        -RunLevel Highest `
        -Force | Out-Null
    
    Write-Host "o Tarefa registrada com sucesso!" -ForegroundColor Green
    Write-Host "  Nome: $taskName" -ForegroundColor Cyan
    Write-Host "  Script: $scriptPath" -ForegroundColor Cyan
    Write-Host "  Acao: Executar na inicializacao do sistema" -ForegroundColor Cyan
    
    # Verificar se foi criada
    $task = Get-ScheduledTask -TaskName $taskName
    Write-Host "`no Tarefa confirmada:" -ForegroundColor Green
    Write-Host "  Habilitada: $($task.Enabled)" -ForegroundColor Cyan
    Write-Host "  Ultima execucao: $($task.LastRunTime)" -ForegroundColor Cyan
    
} catch {
    Write-Host "ERROR: Falha ao registrar tarefa: $_" -ForegroundColor Red
    exit 1
}

Write-Host "`no Configuracao completa!" -ForegroundColor Green
Write-Host "  O servidor SSH-Connect iniciara automaticamente na proxima inicializacao do PC" -ForegroundColor Yellow
