# SSH-Connect MCP Server (Estrutura Enterprise)

Servidor de integração segura SSH-Connect baseado no **Model Context Protocol (MCP)** para suporte a assistentes de Inteligência Artificial (como o Gemini/Antigravity) e IDEs.

Este repositório foi reestruturado sob um padrão corporativo de maturidade sênior, com segregação clara de responsabilidades, isolamento rígido de segredos locais e suite completa de testes integrados.

---

## 📁 Estrutura do Projeto

A nova árvore de diretórios organiza os componentes em camadas lógicas distintas:

* `config/`: Armazena os arquivos de configuração para registro e comportamento dos clientes MCP.
* `docs/`: Documentação profunda da arquitetura do sistema e runbooks de manutenção operacional.
* `logs/`: Logs de auditoria operacional do servidor (gerado em tempo de execução).
* `scripts/`: Utilitários automatizados de ciclo de vida (instalação, registro de serviço e testes rápidos).
* `server/`: Código-fonte central do servidor Python configurado em pacotes modulares.
* `tests/`: Suite completa de testes unitários e de integração (conexão SSH, handlers e protocolo JSON-RPC).

---

## 🚀 Como Iniciar

### 1. Provisionar Ambiente (.venv)
O provisionamento e instalação de dependências são totalmente automatizados através de scripts baseados no empacotador de alta performance `uv`.

Abra o terminal na pasta raiz e execute:
```powershell
powershell -ExecutionPolicy Bypass -File C:\ssh-mcp\scripts\setup.ps1
```
*Este script instalará o `uv` se não estiver no sistema, criará o ambiente virtual isolado `.venv` e instalará a biblioteca em modo editável.*

### 2. Configurar Variáveis locais (.env)
Copie o arquivo de exemplo `.env.example` para `.env` na raiz do projeto e configure suas credenciais do servidor SSH alvo:
```powershell
copy .env.example .env
```
Edite o arquivo `.env` preenchendo as seguintes chaves de acesso:
```env
SSH_HOST=10.0.0.7
SSH_PORT=22
SSH_USERNAME=alessandro.meneses
SSH_PASSWORD=sua_senha_segura
```

### 3. Registrar o Cliente MCP
Substitua ou configure a definição do MCP Server no arquivo JSON de configurações globais do Gemini/Antigravity (`C:\Users\alessandro.meneses.Automotion\.gemini\config\mcp_config.json`):

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

---

## 🩺 Diagnósticos e Testes Rápidos

O projeto conta com diagnóstico automatizado para atestar a saúde da aplicação.

Execute o script abaixo no PowerShell para obter o status em tempo real de 20 pontos de validação:
```powershell
powershell -ExecutionPolicy Bypass -File C:\ssh-mcp\scripts\quick-check.ps1
```

Se precisar rodar testes de integração isolados:
```powershell
# Teste de conexão paramiko pura
C:\ssh-mcp\server\.venv\Scripts\python.exe C:\ssh-mcp\tests\test_connection.py

# Teste de handlers internos do módulo python
C:\ssh-mcp\server\.venv\Scripts\python.exe C:\ssh-mcp\tests\test_mcp_direct.py

# Teste de conformidade do handshake JSON-RPC stdio
C:\ssh-mcp\server\.venv\Scripts\python.exe C:\ssh-mcp\tests\test_mcp_protocol.py
```

---

## 📚 Documentação Técnica Avançada

Consulte a pasta [docs](file:///C:/ssh-mcp/docs) para informações detalhadas:

* **[ARCHITECTURE.md](file:///C:/ssh-mcp/docs/ARCHITECTURE.md)**: Detalhamento sobre o fluxo de ciclo de vida do MCP, topologia física de diretórios e políticas de segurança.
* **[RUNBOOK.md](file:///C:/ssh-mcp/docs/RUNBOOK.md)**: Manual operacional focado em inicialização automática no Windows Startup, gerenciamento de processos órfãos, logs e diagnósticos de erros.
