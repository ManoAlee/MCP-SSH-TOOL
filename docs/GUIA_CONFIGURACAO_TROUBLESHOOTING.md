# Guia de Configuração e Troubleshooting

## 🎯 Configuração Inicial

### Passo 1: Baixar o Repositório

```powershell
# Abra PowerShell
mkdir C:\ssh-mcp
cd C:\ssh-mcp
git clone https://github.com/t-suganuma/ssh-connect-mcp-server.git ssh-connect-mcp-server
```

### Passo 2: Instalar uv

```powershell
# Execute como usuário normal (NÃO precisa de admin)
powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"

# Feche e reabra o PowerShell
# Teste
uv --version
```

### Passo 3: Criar Arquivo de Configuração MCP

**Localização:** `C:\Users\seu_usuario\.gemini\config\mcp_config.json`

```json
{
  "mcpServers": {
    "ssh-connect": {
      "command": "C:\\Users\\seu_usuario\\.local\\bin\\uv.exe",
      "args": [
        "--directory",
        "C:\\ssh-mcp\\ssh-connect-mcp-server",
        "run",
        "ssh-connect"
      ],
      "env": {
        "SSH_HOST": "10.0.0.7",
        "SSH_PORT": "22",
        "SSH_USERNAME": "seu_usuario_ssh",
        "SSH_PASSWORD": "sua_senha_ssh",
        "PATH": "C:\\Users\\seu_usuario\\.local\\bin;C:\\Windows\\System32;C:\\Windows"
      }
    }
  }
}
```

**Não esqueça de:**
- Trocar `seu_usuario` pelo seu usuário Windows
- Trocar `seu_usuario_ssh` pelo seu usuário SSH
- Trocar `sua_senha_ssh` pela sua senha SSH

### Passo 4: Registrar Inicialização Automática

**Opção A: Manualmente (recomendado)**

```powershell
# Crie um atalho manualmente
$batPath = "C:\ssh-mcp\StartSSHMCP.bat"
$lnkPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\SSH-Connect-MCP.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($lnkPath)
$shortcut.TargetPath = $batPath
$shortcut.WindowStyle = 7  # Hidden
$shortcut.Save()
```

**Opção B: Como Administrator**

```powershell
# Execute como Administrator
powershell -ExecutionPolicy Bypass -File "C:\ssh-mcp\Register-StartupTask.ps1"
```

### Passo 5: Teste a Configuração

```powershell
# Teste manual
cd C:\ssh-mcp\ssh-connect-mcp-server
$env:Path = "C:\Users\seu_usuario\.local\bin;$env:Path"

# Execute o servidor
uv run ssh-connect

# Você verá a mensagem indicando que o servidor está aguardando conexões
# Pressione Ctrl+C para parar
```

### Passo 6: Reinicie e Valide

```powershell
# Reinicie o PC
Restart-Computer

# Após reinicializar, verifique se o servidor iniciou
Get-Content "C:\ssh-mcp\ssh-mcp.log" -Tail 10
```

---

## 🔧 Troubleshooting

### Problema 1: "uv: The term 'uv' is not recognized"

**Causa:** uv não está no PATH

**Solução:**
```powershell
# Verifique se uv foi instalado
Test-Path "C:\Users\seu_usuario\.local\bin\uv.exe"

# Se existir, adicione ao PATH temporariamente
$env:Path = "C:\Users\seu_usuario\.local\bin;$env:Path"

# Se não existir, reinstale
powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
```

---

### Problema 2: "Erro spawn uv ENOENT" no Antigravity

**Causa:** Antigravity não consegue encontrar o comando `uv`

**Solução:**

Edite `mcp_config.json` e use o caminho completo:

```json
"command": "C:\\Users\\seu_usuario\\.local\\bin\\uv.exe"
```

Em vez de:

```json
"command": "uv"
```

---

### Problema 3: Falha de Autenticação SSH

**Causa:** Credenciais incorretas ou servidor inacessível

**Verificação:**
```powershell
# 1. Teste conectividade
ping 10.0.0.7
Test-NetConnection -ComputerName "10.0.0.7" -Port 22

# 2. Teste credenciais
cd C:\ssh-mcp\ssh-connect-mcp-server
$env:Path = "C:\Users\seu_usuario\.local\bin;$env:Path"
uv run python C:\ssh-mcp\test_ssh_direct.py

# 3. Verifique arquivo de configuração
Get-Content "C:\Users\seu_usuario\.gemini\config\mcp_config.json" | ConvertFrom-Json
```

**Solução:**
- Verifique se as credenciais estão corretas (sem espaços extras)
- Teste com um cliente SSH diferente (PuTTY, etc.)
- Verifique se o servidor SSH está rodando: `ssh-v`

---

### Problema 4: Servidor Não Inicia Automaticamente

**Causa:** Atalho não foi criado ou permissões insuficientes

**Verificação:**
```powershell
# Verifique se o atalho existe
Test-Path "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\SSH-Connect-MCP.lnk"

# Verifique se o arquivo batch existe
Test-Path "C:\ssh-mcp\StartSSHMCP.bat"

# Verifique o log de inicialização
Get-Content "C:\ssh-mcp\ssh-mcp.log"
```

**Solução:**
```powershell
# Recrie o atalho
$batPath = "C:\ssh-mcp\StartSSHMCP.bat"
$lnkPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\SSH-Connect-MCP.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($lnkPath)
$shortcut.TargetPath = $batPath
$shortcut.WindowStyle = 7
$shortcut.Save()

# Verifique se foi criado
Test-Path $lnkPath
```

---

### Problema 5: "ModuleNotFoundError" ao Executar

**Causa:** Dependências não instaladas ou ambiente incorreto

**Solução:**
```powershell
# Reinstale as dependências
cd C:\ssh-mcp\ssh-connect-mcp-server
$env:Path = "C:\Users\seu_usuario\.local\bin;$env:Path"
uv lock --upgrade
```

---

### Problema 6: Antigravity Não Vê o Servidor MCP

**Causa:** Arquivo de configuração inválido ou em local errado

**Verificação:**
```powershell
# Verifique os locais de configuração
Test-Path "C:\Users\seu_usuario\.gemini\config\mcp_config.json"
Test-Path "C:\Users\seu_usuario\.gemini\antigravity\mcp_config.json"

# Verifique o conteúdo
Get-Content "C:\Users\seu_usuario\.gemini\config\mcp_config.json" | ConvertFrom-Json
```

**Solução:**
1. Certifique-se de que o arquivo é JSON válido
2. Reinicie o Antigravity
3. Aguarde 5-10 segundos para carregar

---

### Problema 7: Conexão SSH Muito Lenta

**Causa:** Latência alta ou problema de rede

**Verificação:**
```powershell
# Medir latência
ping 10.0.0.7 -Count 4

# Verificar rota
tracert 10.0.0.7

# Testar porta SSH
Test-NetConnection -ComputerName "10.0.0.7" -Port 22 -InformationLevel Detailed
```

**Solução:**
- Verifique conexão de rede
- Aumente timeout nos argumentos do comando
- Teste conectividade diretamente com SSH

---

### Problema 8: Arquivo de Log Muito Grande

**Causa:** Muitas operações registradas

**Solução:**
```powershell
# Ver tamanho do log
Get-Item "C:\ssh-mcp\ssh-mcp.log" | Select-Object Length

# Limpar log
Clear-Content "C:\ssh-mcp\ssh-mcp.log"

# Ou rotacionar
Move-Item "C:\ssh-mcp\ssh-mcp.log" "C:\ssh-mcp\ssh-mcp.log.$(Get-Date -Format 'yyyy-MM-dd')" -Force
```

---

## 📊 Testes de Validação

### Teste 1: Verificação Rápida
```powershell
powershell -ExecutionPolicy Bypass -File "C:\ssh-mcp\quick-check.ps1"
```

### Teste 2: Validação Técnica Completa
```powershell
# Leia o relatório
Get-Content "C:\ssh-mcp\VALIDATION_REPORT.md" | Out-Host -Paging
```

### Teste 3: SSH Direto
```powershell
cd C:\ssh-mcp\ssh-connect-mcp-server
$env:Path = "C:\Users\seu_usuario\.local\bin;$env:Path"
uv run python C:\ssh-mcp\test_ssh_direct.py
```

### Teste 4: Servidor MCP
```powershell
# Inicie manualmente
cd C:\ssh-mcp\ssh-connect-mcp-server
$env:Path = "C:\Users\seu_usuario\.local\bin;$env:Path"
uv run ssh-connect

# Você verá logs indicando que o servidor está pronto
```

---

## 🔍 Debug Avançado

### Ver Logs em Tempo Real
```powershell
Get-Content "C:\ssh-mcp\ssh-mcp.log" -Wait
```

### Verificar Processos
```powershell
# Ver processos Python e uv
Get-Process | Where-Object {$_.ProcessName -like "*python*" -or $_.ProcessName -like "*uv*"}

# Matar processo (se necessário)
Stop-Process -Name "*python*" -Force
Stop-Process -Name "*uv*" -Force
```

### Verificar PATH do Sistema
```powershell
# Ver PATH completo
$env:Path -split ";" | Select-Object -First 20

# Ver variáveis de ambiente específicas
[Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
```

### Testar JSON de Configuração
```powershell
# Verificar se é JSON válido
$json = Get-Content "C:\Users\seu_usuario\.gemini\config\mcp_config.json" | ConvertFrom-Json
$json | ConvertTo-Json -Depth 10 | Out-Host -Paging
```

---

## 📋 Checklist de Setup

- [ ] uv instalado (`uv --version`)
- [ ] Repositório clonado em `C:\ssh-mcp\ssh-connect-mcp-server`
- [ ] Arquivo `mcp_config.json` criado com credenciais corretas
- [ ] Caminho de `uv.exe` correto no `mcp_config.json`
- [ ] Atalho criado em Startup
- [ ] Teste manual bem-sucedido (`test_ssh_direct.py`)
- [ ] PC reiniciado
- [ ] Log criado (`ssh-mcp.log`)
- [ ] Antigravity vê o servidor MCP
- [ ] Comando `use_mcp_tool` funciona

---

## 💾 Backup e Recuperação

### Backup de Configuração
```powershell
# Criar backup
Copy-Item "C:\Users\seu_usuario\.gemini\config\mcp_config.json" "C:\ssh-mcp\backup\mcp_config.json.$(Get-Date -Format 'yyyy-MM-dd-HHmmss').json"

# Restaurar
Copy-Item "C:\ssh-mcp\backup\mcp_config.json.2026-05-21.json" "C:\Users\seu_usuario\.gemini\config\mcp_config.json"
```

### Reimplementar do Zero
```powershell
# Se algo quebrar, execute:
# 1. Remova o atalho
Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\SSH-Connect-MCP.lnk" -Force

# 2. Recrie a configuração MCP
# Use as instruções de Passo 3

# 3. Recrie o atalho
# Use as instruções de Passo 4

# 4. Reinicie
Restart-Computer
```

---

**Última atualização:** 21 de maio de 2026  
**Versão:** 1.0.0  
**Status:** ✓ DOCUMENTADO
