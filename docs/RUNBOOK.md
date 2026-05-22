# Runbook de OperaÃ§Ãµes - SSH-Connect MCP Server

Este manual de operaÃ§Ãµes fornece instruÃ§Ãµes de nÃ­vel corporativo para instalaÃ§Ã£o, manutenÃ§Ã£o diÃ¡ria, diagnÃ³stico de problemas e monitoramento de saÃºde do **SSH-Connect MCP Server**.

---

## 1. Ciclo de Vida e OperaÃ§Ã£o do Servidor

### InicializaÃ§Ã£o AutomÃ¡tica no Windows
O servidor Ã© projetado para iniciar automaticamente na inicializaÃ§Ã£o do Windows de duas formas:
1. **Pasta Inicializar (Startup folder)**: Um atalho de atalho invisÃ­vel aponta para `C:\ssh-mcp\scripts\StartSSHMCP.bat`.
2. **Agendador de Tarefas do Windows**: Registrado via PowerShell de forma resiliente.

Para registrar a tarefa automÃ¡tica de inicializaÃ§Ã£o corporativa:
1. Abra o PowerShell como Administrador.
2. Execute o comando:
   ```powershell
   powershell -ExecutionPolicy Bypass -File C:\ssh-mcp\scripts\Register-StartupTask.ps1
   ```

### InicializaÃ§Ã£o Manual para Testes
Caso queira testar a execuÃ§Ã£o ou ver saÃ­das do terminal:
```powershell
# Executar utilizando o binÃ¡rio compilado no ambiente virtual
C:\ssh-mcp\server\.venv\Scripts\ssh-connect.exe
```

### Parada e ReinicializaÃ§Ã£o
Para parar processos Ã³rfÃ£os ou reiniciar o servidor travado por processos em background, execute no PowerShell:
```powershell
# Encontrar e encerrar processos associados
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*ssh-connect*" -or $_.CommandLine -like "*ssh_connect*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

---

## 2. ConfiguraÃ§Ãµes Globais dos Clientes MCP

### ConfiguraÃ§Ã£o do Gemini / Antigravity
O arquivo de configuraÃ§Ã£o do cliente deve apontar para o novo diretÃ³rio organizado em `C:\ssh-mcp\server`.
Edite os seguintes caminhos no seu arquivo de configuraÃ§Ã£o do cliente (localizados em `C:\Users\<YOUR_USER>\.gemini\config\mcp_config.json` e `C:\Users\<YOUR_USER>\.gemini\antigravity\mcp_config.json`):

```json
{
  "mcpServers": {
    "ssh-connect": {
      "command": "C:\\ssh-mcp\\server\\.venv\\Scripts\\ssh-connect.exe",
      "args": [],
      "cwd": "C:\\ssh-mcp\\server",
      "env": {
        "PATH": "C:\\Windows\\System32;C:\\Windows"
      }
    }
  }
}
```

*Nota: NÃ£o Ã© necessÃ¡rio declarar credenciais de conexÃ£o na propriedade `env` acima. O servidor Python carrega automaticamente as variÃ¡veis declaradas no arquivo `.env` localizado na raiz do projeto (`C:\ssh-mcp\.env`).*

---

## 3. DiagnÃ³stico e Suite de Testes

Temos um script de diagnÃ³stico automatizado de 20 testes que valida desde a integridade fÃ­sica dos diretÃ³rios atÃ© a conectividade de rede com o servidor SSH.

### Executando DiagnÃ³stico RÃ¡pido (20 testes)
```powershell
powershell -ExecutionPolicy Bypass -File C:\ssh-mcp\scripts\quick-check.ps1
```

### Executando Suite de Testes TÃ©cnicos
Se os testes rÃ¡pidos passarem mas houver problemas na execuÃ§Ã£o das ferramentas MCP, execute os testes tÃ©cnicos integrados:

1. **Teste de ConexÃ£o Paramiko pura**:
   Verifica se as credenciais fornecidas no `.env` e as rotas de rede conseguem estabelecer sessÃ£o SSH com sucesso.
   ```powershell
   C:\ssh-mcp\server\.venv\Scripts\python.exe C:\ssh-mcp\tests\test_connection.py
   ```

2. **Teste dos Handlers Python Internos**:
   Valida se a lÃ³gica interna do cÃ³digo Python estÃ¡ interpretando corretamente as credenciais do `.env` sem crashes.
   ```powershell
   C:\ssh-mcp\server\.venv\Scripts\python.exe C:\ssh-mcp\tests\test_mcp_direct.py
   ```

3. **Teste de Handshake do Protocolo JSON-RPC**:
   Testa a comunicaÃ§Ã£o via Stdio de ponta a ponta gerando mensagens RPC e validando a resposta do servidor.
   ```powershell
   C:\ssh-mcp\server\.venv\Scripts\python.exe C:\ssh-mcp\tests\test_mcp_protocol.py
   ```

---

## 4. ResoluÃ§Ã£o de Problemas (Troubleshooting)

### A. Erro: "Server timed out" ou Travamento de InicializaÃ§Ã£o
* **Causa**: Processos Python/UV antigos mantÃªm a porta de comunicaÃ§Ã£o presa ou hÃ¡ um lock de arquivos pendente.
* **SoluÃ§Ã£o**: Mate os processos ativos (consulte a seÃ§Ã£o **Parada e ReinicializaÃ§Ã£o** deste documento) e verifique o arquivo de log `logs/ssh-mcp.log` para encontrar tracebacks especÃ­ficos.

### B. Erro de Unicode: `UnicodeEncodeError` no Console Windows
* **Causa**: O console do Windows executando codificaÃ§Ã£o legada ANSI (CP1252) falha ao renderizar sÃ­mbolos especiais como `âœ“` ou `âœ—`.
* **SoluÃ§Ã£o**: Garantimos que toda a saÃ­da padrÃ£o do sistema use apenas strings ASCII. Certifique-se de que nenhum print customizado contenha caracteres Unicode sem a codificaÃ§Ã£o adequada configurada no Python.

### C. Erro de Conectividade SSH (Timeout ou Authentication Failed)
* **Causa**: Firewall bloqueando a porta 22, credenciais incorretas ou formato invÃ¡lido do `.env`.
* **SoluÃ§Ã£o**:
  1. Teste o alcance da rede com `Test-NetConnection -ComputerName <SSH_HOST> -Port <SSH_PORT>`.
  2. Abra `C:\ssh-mcp\.env` e valide se as credenciais nÃ£o contÃªm aspas extras ou espaÃ§os em branco ao redor dos valores das propriedades.

