# Runbook de Operações - SSH-Connect MCP Server

Este manual de operações fornece instruções de nível corporativo para instalação, manutenção diária, diagnóstico de problemas e monitoramento de saúde do **SSH-Connect MCP Server**.

---

## 1. Ciclo de Vida e Operação do Servidor

### Inicialização Automática no Windows
O servidor é projetado para iniciar automaticamente na inicialização do Windows de duas formas:
1. **Pasta Inicializar (Startup folder)**: Um atalho de atalho invisível aponta para `C:\ssh-mcp\scripts\StartSSHMCP.bat`.
2. **Agendador de Tarefas do Windows**: Registrado via PowerShell de forma resiliente.

Para registrar a tarefa automática de inicialização corporativa:
1. Abra o PowerShell como Administrador.
2. Execute o comando:
   ```powershell
   powershell -ExecutionPolicy Bypass -File C:\ssh-mcp\scripts\Register-StartupTask.ps1
   ```

### Inicialização Manual para Testes
Caso queira testar a execução ou ver saídas do terminal:
```powershell
# Executar utilizando o binário compilado no ambiente virtual
C:\ssh-mcp\server\.venv\Scripts\ssh-connect.exe
```

### Parada e Reinicialização
Para parar processos órfãos ou reiniciar o servidor travado por processos em background, execute no PowerShell:
```powershell
# Encontrar e encerrar processos associados
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*ssh-connect*" -or $_.CommandLine -like "*ssh_connect*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

---

## 2. Configurações Globais dos Clientes MCP

### Configuração do Gemini / Antigravity
O arquivo de configuração do cliente deve apontar para o novo diretório organizado em `C:\ssh-mcp\server`.
Edite os seguintes caminhos no seu arquivo de configuração do cliente (localizados em `C:\Users\alessandro.meneses.Automotion\.gemini\config\mcp_config.json` e `C:\Users\alessandro.meneses.Automotion\.gemini\antigravity\mcp_config.json`):

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

*Nota: Não é necessário declarar credenciais de conexão na propriedade `env` acima. O servidor Python carrega automaticamente as variáveis declaradas no arquivo `.env` localizado na raiz do projeto (`C:\ssh-mcp\.env`).*

---

## 3. Diagnóstico e Suite de Testes

Temos um script de diagnóstico automatizado de 20 testes que valida desde a integridade física dos diretórios até a conectividade de rede com o servidor SSH.

### Executando Diagnóstico Rápido (20 testes)
```powershell
powershell -ExecutionPolicy Bypass -File C:\ssh-mcp\scripts\quick-check.ps1
```

### Executando Suite de Testes Técnicos
Se os testes rápidos passarem mas houver problemas na execução das ferramentas MCP, execute os testes técnicos integrados:

1. **Teste de Conexão Paramiko pura**:
   Verifica se as credenciais fornecidas no `.env` e as rotas de rede conseguem estabelecer sessão SSH com sucesso.
   ```powershell
   C:\ssh-mcp\server\.venv\Scripts\python.exe C:\ssh-mcp\tests\test_connection.py
   ```

2. **Teste dos Handlers Python Internos**:
   Valida se a lógica interna do código Python está interpretando corretamente as credenciais do `.env` sem crashes.
   ```powershell
   C:\ssh-mcp\server\.venv\Scripts\python.exe C:\ssh-mcp\tests\test_mcp_direct.py
   ```

3. **Teste de Handshake do Protocolo JSON-RPC**:
   Testa a comunicação via Stdio de ponta a ponta gerando mensagens RPC e validando a resposta do servidor.
   ```powershell
   C:\ssh-mcp\server\.venv\Scripts\python.exe C:\ssh-mcp\tests\test_mcp_protocol.py
   ```

---

## 4. Resolução de Problemas (Troubleshooting)

### A. Erro: "Server timed out" ou Travamento de Inicialização
* **Causa**: Processos Python/UV antigos mantêm a porta de comunicação presa ou há um lock de arquivos pendente.
* **Solução**: Mate os processos ativos (consulte a seção **Parada e Reinicialização** deste documento) e verifique o arquivo de log `logs/ssh-mcp.log` para encontrar tracebacks específicos.

### B. Erro de Unicode: `UnicodeEncodeError` no Console Windows
* **Causa**: O console do Windows executando codificação legada ANSI (CP1252) falha ao renderizar símbolos especiais como `✓` ou `✗`.
* **Solução**: Garantimos que toda a saída padrão do sistema use apenas strings ASCII. Certifique-se de que nenhum print customizado contenha caracteres Unicode sem a codificação adequada configurada no Python.

### C. Erro de Conectividade SSH (Timeout ou Authentication Failed)
* **Causa**: Firewall bloqueando a porta 22, credenciais incorretas ou formato inválido do `.env`.
* **Solução**:
  1. Teste o alcance da rede com `Test-NetConnection -ComputerName <SSH_HOST> -Port <SSH_PORT>`.
  2. Abra `C:\ssh-mcp\.env` e valide se as credenciais não contêm aspas extras ou espaços em branco ao redor dos valores das propriedades.
