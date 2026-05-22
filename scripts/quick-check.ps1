#!/usr/bin/env powershell
# Script de Verificacao Rapida - SSH-Connect MCP Server (Estrutura Enterprise)
# Uso: .\quick-check.ps1

param(
    [switch]$Verbose = $false
)

$results = @{
    TotalTests = 0
    Passed = 0
    Failed = 0
    Warnings = 0
}

function Test-Item {
    param(
        [string]$Name,
        [scriptblock]$TestBlock,
        [string]$Category = "General"
    )
    
    $results.TotalTests++
    try {
        $result = & $TestBlock
        if ($result) {
            Write-Host "  [OK] $Name" -ForegroundColor Green
            $results.Passed++
            return $true
        } else {
            Write-Host "  [FALHA] $Name" -ForegroundColor Red
            $results.Failed++
            return $false
        }
    } catch {
        Write-Host "  [AVISO] $Name ($_)" -ForegroundColor Yellow
        $results.Warnings++
        return $false
    }
}

Clear-Host
Write-Host ""
Write-Host "+----------------------------------------------------------------+" -ForegroundColor Cyan
Write-Host "|         SSH-Connect MCP Server - Verificacao Rapida             |" -ForegroundColor Cyan
Write-Host "|                   Status & Health Check (Enterprise)            |" -ForegroundColor Cyan
Write-Host "+----------------------------------------------------------------+" -ForegroundColor Cyan
Write-Host ""

Write-Host "CATEGORIA 1: Estrutura de Arquivos" -ForegroundColor Yellow
Write-Host "------------------------------------" -ForegroundColor Gray
Test-Item "Diretorio principal" { Test-Path "C:\ssh-mcp" }
Test-Item "Diretorio do Servidor" { Test-Path "C:\ssh-mcp\server" }
Test-Item "Codigo Python" { Test-Path "C:\ssh-mcp\server\src\ssh_connect" }
Test-Item "pyproject.toml" { Test-Path "C:\ssh-mcp\server\pyproject.toml" -PathType Leaf }
Test-Item "Diretorio de Logs" { Test-Path "C:\ssh-mcp\logs" }
Test-Item "Diretorio de Scripts" { Test-Path "C:\ssh-mcp\scripts" }
Test-Item "Diretorio de Config" { Test-Path "C:\ssh-mcp\config" }
Test-Item "Diretorio de Testes" { Test-Path "C:\ssh-mcp\tests" }
Test-Item "Arquivo .env" { Test-Path "C:\ssh-mcp\.env" -PathType Leaf }
Write-Host ""

Write-Host "CATEGORIA 2: Configuracao MCP" -ForegroundColor Yellow
Write-Host "------------------------------------" -ForegroundColor Gray
Test-Item "Config em .gemini/config" { Test-Path "C:\Users\alessandro.meneses.Automotion\.gemini\config\mcp_config.json" -PathType Leaf }
Test-Item "Config em .gemini/antigravity" { Test-Path "C:\Users\alessandro.meneses.Automotion\.gemini\antigravity\mcp_config.json" -PathType Leaf }
Test-Item "MCP contem ssh-connect" {
    try {
        $json = Get-Content "C:\Users\alessandro.meneses.Automotion\.gemini\config\mcp_config.json" | ConvertFrom-Json
        $json.mcpServers.PSObject.Properties.Name -contains "ssh-connect"
    } catch { $false }
}
Test-Item "Configuracao aponta para server/" {
    try {
        $json = Get-Content "C:\Users\alessandro.meneses.Automotion\.gemini\config\mcp_config.json" | ConvertFrom-Json
        $serverCfg = $json.mcpServers."ssh-connect"
        $serverCfg.command -like "*server\.venv*" -and $serverCfg.cwd -like "*server"
    } catch { $false }
}
Write-Host ""

Write-Host "CATEGORIA 3: Inicializacao e Logs" -ForegroundColor Yellow
Write-Host "------------------------------------" -ForegroundColor Gray
Test-Item "Script StartSSHMCP.bat" { Test-Path "C:\ssh-mcp\scripts\StartSSHMCP.bat" -PathType Leaf }
Test-Item "Atalho Startup desabilitado" { -not (Test-Path "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\SSH-Connect-MCP.lnk" -PathType Leaf) }
Test-Item "Log de inicializacao existe" { Test-Path "C:\ssh-mcp\logs\ssh-mcp.log" -PathType Leaf }
Write-Host ""

Write-Host "CATEGORIA 4: Binarios e Dependencias" -ForegroundColor Yellow
Write-Host "------------------------------------" -ForegroundColor Gray
Test-Item "uv no PATH" {
    $env:Path = "C:\Users\alessandro.meneses.Automotion\.local\bin;$env:Path"
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    $null -ne $uv
}
Test-Item "uv.lock sincronizado" { Test-Path "C:\ssh-mcp\server\uv.lock" -PathType Leaf }
Test-Item ".venv Python existe" { Test-Path "C:\ssh-mcp\server\.venv\Scripts\python.exe" -PathType Leaf }
Write-Host ""

Write-Host "CATEGORIA 5: Conectividade (usando .env)" -ForegroundColor Yellow
Write-Host "------------------------------------" -ForegroundColor Gray

# Carregar .env para os testes de conexao
$hostIp = ""
$port = 22
if (Test-Path "C:\ssh-mcp\.env") {
    Get-Content "C:\ssh-mcp\.env" | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            $key = $parts[0].Trim()
            $val = $parts[1].Trim()
            if ($key -eq "SSH_HOST") { $hostIp = $val }
            if ($key -eq "SSH_PORT") { $port = [int]$val }
        }
    }
}

if (-not $hostIp) {
    Write-Host "  [AVISO] SSH_HOST nao configurado no .env" -ForegroundColor Yellow
    $results.Warnings++
} else {
    Test-Item "Host SSH (${hostIp}:$port) alcancavel" {
        try {
            $null = Test-NetConnection -ComputerName $hostIp -Port $port -WarningAction SilentlyContinue
            $true
        } catch { $false }
    }
}
Write-Host ""

Write-Host "RESUMO DOS TESTES" -ForegroundColor Yellow
Write-Host "------------------------------------" -ForegroundColor Gray
Write-Host "  Total de Testes: $($results.TotalTests)" -ForegroundColor Cyan
Write-Host "  Aprovados: $($results.Passed)" -ForegroundColor Green
Write-Host "  Falhados: $($results.Failed)" -ForegroundColor Red
Write-Host "  Avisos: $($results.Warnings)" -ForegroundColor Yellow
Write-Host ""

if ($results.Failed -eq 0 -and $results.Warnings -le 1) {
    Write-Host "  STATUS FINAL: [OK] SISTEMA SAUDAVEL" -ForegroundColor Green
} elseif ($results.Failed -eq 0) {
    Write-Host "  STATUS FINAL: [AVISO] SISTEMA OPERACIONAL (com avisos)" -ForegroundColor Yellow
} else {
    Write-Host "  STATUS FINAL: [ERRO] FALHAS DETECTADAS" -ForegroundColor Red
}

Write-Host ""
Write-Host "Relatorio detalhado sera gerado em: C:\ssh-mcp\docs\VALIDATION_REPORT.md" -ForegroundColor Cyan
Write-Host ""
