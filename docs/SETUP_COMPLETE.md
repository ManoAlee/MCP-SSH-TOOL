# Configuração de Inicialização Automática - SSH-Connect MCP Server

## ✅ O QUE FOI CONFIGURADO

### 1. Scripts de Inicialização
- **C:\ssh-mcp\StartSSHMCP.bat** - Script principal que inicia o servidor
- **C:\ssh-mcp\Start-SSHMCPServer.ps1** - Script PowerShell (opcional)
- **C:\ssh-mcp\Register-StartupTask.ps1** - Script para tarefa agendada (opcional)

### 2. Inicialização Automática
- **Atalho criado em:** `C:\Users\alessandro.meneses.Automotion\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\SSH-Connect-MCP.lnk`
- **Tipo:** Inicialização na pasta Startup do Windows
- **Execução:** Automática sempre que o PC liga

### 3. Variáveis de Ambiente
- **uv adicionado ao PATH:** C:\Users\alessandro.meneses.Automotion\.local\bin
- **Permissão:** Permanente (registrado nas variáveis de usuário)

### 4. Configuração MCP
- **Local 1:** C:\Users\alessandro.meneses.Automotion\.gemini\config\mcp_config.json
- **Local 2:** C:\Users\alessandro.meneses.Automotion\.gemini\antigravity\mcp_config.json
- **Status:** ✓ Configurado com servidor SSH 10.0.0.7

### 5. Logging
- **Arquivo de log:** C:\ssh-mcp\ssh-mcp.log
- **Arquivo PID:** C:\ssh-mcp\ssh-mcp.pid
- **Rastreamento:** Todas as inicializações são registradas

---

## 🚀 COMO FUNCIONA

### Na Inicialização do PC:
1. O Windows executa o atalho na pasta Startup
2. O arquivo `StartSSHMCP.bat` é executado
3. Adiciona uv ao PATH
4. Navega para C:\ssh-mcp\ssh-connect-mcp-server
5. Executa: `uv run ssh-connect`
6. O servidor MCP inicia em background
7. Registra a execução no arquivo de log

### No Antigravity:
1. Após o PC inicializar, o servidor estará disponível automaticamente
2. Use normalmente:
```
use_mcp_tool(server_name="ssh-connect", tool_name="connect", arguments={})
```

---

## 📋 VERIFICAR SE ESTÁ FUNCIONANDO

### Verificar o Log:
```powershell
Get-Content "C:\ssh-mcp\ssh-mcp.log" -Tail 20
```

### Verificar se o Atalho Existe:
```powershell
Get-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\SSH-Connect-MCP.lnk"
```

### Testar Manualmente:
```cmd
C:\ssh-mcp\StartSSHMCP.bat
```

### Verificar Processos Rodando:
```powershell
Get-Process | Where-Object {$_.ProcessName -like "*uv*" -or $_.ProcessName -like "*python*"}
```

---

## ⚙️ SE PRECISAR PARAR O SERVIDOR

### Opção 1 - Matar o Processo:
```powershell
Stop-Process -Name "*uv*" -Force
Stop-Process -Name "*python*" -Force
```

### Opção 2 - Remover do Startup:
```powershell
Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\SSH-Connect-MCP.lnk" -Force
```

### Opção 3 - Desabilitar Tarefa (se registrada):
```powershell
Disable-ScheduledTask -TaskName "SSH-Connect MCP Server"
```

---

## 🔧 CONFIGURAÇÃO DO SERVIDOR SSH

**Host:** 10.0.0.7  
**Porta:** 22  
**Usuário:** alessandro.meneses  
**Autenticação:** Senha  

As credenciais estão armazenadas em:
- `C:\Users\alessandro.meneses.Automotion\.gemini\config\mcp_config.json`
- `C:\Users\alessandro.meneses.Automotion\.gemini\antigravity\mcp_config.json`

---

## ✅ RESUMO FINAL

- ✓ Servidor SSH-Connect configurado e testado
- ✓ Inicialização automática registrada na Startup
- ✓ uv adicionado ao PATH permanentemente
- ✓ Arquivos de configuração MCP criados
- ✓ Sistema de logging implementado
- ✓ Pronto para uso imediato após reinicialização

**Próxima ação:** Reinicie o PC para confirmar que o servidor inicia automaticamente!
