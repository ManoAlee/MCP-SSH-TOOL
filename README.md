# 🚀 MCP Híbrido: SSH & Windows Domain PowerShell Tool
### *Enterprise-Grade Integration Server for AI-Driven System Administration*

```text
███████╗███████╗██╗  ██╗      ███╗   ███╗ ██████╗██████╗     ████████╗ ██████╗  ██████╗ ██╗     
██╔════╝██╔════╝██║  ██║      ████╗ ████║██╔════╝██╔═══██╗    ╚══██╔══╝██╔═══██╗██╔═══██╗██║     
███████╗███████╗███████║█████╗██╔████╔██║██║     ██████╔╝       ██║   ██║   ██║██║   ██║██║     
╚════██║╚════██║██╔══██║╚════╝██║╚██╔╝██║██║     ██╔═══╝        ██║   ██║   ██║██║   ██║██║     
███████║███████║██║  ██║      ██║ ╚═╝ ██║╚██████╗██║            ██║   ╚██████╔╝╚██████╔╝███████╗
╚══════╝╚══════╝╚═╝  ╚═╝      ╚═╝     ╚═╝ ╚═════╝╚═╝            ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝
```

---

[![Model Context Protocol](https://img.shields.io/badge/MCP-Compliant%20v1.6.0-green.svg?style=for-the-badge&logo=proto&logoColor=white&color=00c853)](https://modelcontextprotocol.io/)
[![PowerShell](https://img.shields.io/badge/PowerShell-5.1%20%7C%207%2B-blue.svg?style=for-the-badge&logo=powershell&logoColor=white)](https://microsoft.com/powershell)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Managed by UV](https://img.shields.io/badge/Managed%20by-UV-black.svg?style=for-the-badge&logo=python&logoColor=white&color=black)](https://github.com/astral-sh/uv)
[![Security](https://img.shields.io/badge/Security-Zero_Trust_SSO-success.svg?style=for-the-badge&logo=snyk&logoColor=white&color=success)](https://owasp.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blueviolet.svg?style=for-the-badge)](https://github.com/ManoAlee/MCP-SSH-TOOL)

O **MCP Híbrido: SSH & PowerShell Tool** é uma ponte de integração corporativa de alto desempenho construída sob a especificação oficial do **Model Context Protocol (MCP)**. Ele permite que assistentes de IA (como Gemini, Claude, Cursor e Windsurf) administrem infraestruturas híbridas complexas com total segurança, suportando de forma nativa:
1. **Ambientes Unix/Linux/macOS** via sessões criptografadas **SSH & SFTP** (utilizando Paramiko).
2. **Infraestruturas Windows Active Directory (Domínio)** via sessões remotas **PowerShell & WinRM** (utilizando Kerberos SSO nativo).

---

## 💡 Recursos de Engenharia (Core Features)

* **🔐 Autenticação por Domínio Transparente (Kerberos SSO)**:
  Em ambientes de domínio Active Directory, o servidor MCP herda as credenciais do seu usuário Windows local. Comandos remotos via `Invoke-Command` utilizam SSO automático, eliminando a necessidade de expor ou trafegar senhas na rede.
* **⚡ Invocação Assíncrona Ultrassegura (`powershell_invoke`)**:
  Todos os comandos enviados ao terminal do Windows são envelopados e transmitidos via `-EncodedCommand` em Base64 (UTF-16LE). Isso neutraliza completamente quaisquer falhas de escape de aspas (`'"`), caracteres especiais ou injeções de script.
* **📂 Subsistema SFTP & WinRM Session File Transfer**:
  - **Linux/Unix**: Envio e recebimento bidirecional via SFTP robusto.
  - **Windows**: Transferência direta de arquivos usando sessões PowerShell (`New-PSSession`) e comandos `Copy-Item -ToSession / -FromSession` sobre o canal WinRM, sem necessidade de compartilhar pastas na rede (SMB).
* **🎯 Retorno de Dados Estruturados (JSON Parsing Nativo)**:
  A listagem de diretórios (`list_files`) no modo Windows executa consultas estruturadas via PowerShell e devolve dados formatados em JSON (`ConvertTo-Json -Compress`), evitando o uso de expressões regulares frágeis sobre saídas de texto brutas.

---

## 🧭 Arquitetura de Fluxo de Dados e Segurança

O diagrama abaixo ilustra como as chamadas JSON-RPC stdio do seu cliente MCP são processadas pelo servidor e direcionadas de forma isolada aos servidores de destino.

```mermaid
flowchart TD
    A[Cliente MCP: Claude / Cursor] <-->|JSON-RPC via Stdio| B(Servidor MCP Híbrido)
    B -->|Lê configurações| C[.env local / Variáveis de Ambiente]
    
    subgraph Modo Linux/macOS
        B -->|Sessão SSH Persistente| D[Cliente Paramiko SSH/SFTP]
        D -->|Porta 22| E[Servidor Remoto Unix]
    end
    
    subgraph Modo Windows Domain
        B -->|Subprocesso Assíncrono| F[powershell.exe -EncodedCommand]
        F -->|Kerberos SSO / WinRM| G[Invoke-Command -ComputerName]
        G -->|Porta 5985/5986| H[Máquina Windows Remota]
    end
```

---

## 🔌 API Reference: Catálogo de Ferramentas MCP

O servidor expõe **7 ferramentas especializadas** prontas para consumo automático pela IA:

### 1. `connect`
Inicializa e valida a sessão ativa no host de destino.
* **Parâmetros**:
  - `host` (string, obrigatório): IP ou Hostname da máquina.
  - `mode` (string): `"ssh"` (padrão) ou `"powershell"` (para máquinas Windows).
  - `username` / `password` (string, opcional): Credenciais explícitas (se omitidos no modo powershell, usa SSO).
  - `port` / `key_path` / `key_passphrase` (opcional): Apenas para conexões SSH.
* **Exemplo de Resposta**: `"Connected to lab-mramos via PowerShell/WinRM (Domain authentication)"`

### 2. `disconnect`
Encerra graciosamente a sessão de rede ativa e limpa os buffers de memória.

### 3. `execute`
Executa um comando na sessão/computador conectado.
* **Parâmetros**:
  - `command` (string, obrigatório): Comando Shell ou PowerShell.
  - `timeout` (integer, opcional): Limite de tempo em segundos (padrão: 60).
* **Exemplo de Resposta**: Retorna o `Exit status`, `STDOUT` e `STDERR`.

### 4. `list_files`
Lista arquivos e pastas de forma estruturada detalhando tipo e tamanho em bytes.
* **Parâmetros**:
  - `path` (string, obrigatório): Caminho absoluto da pasta remota.

### 5. `upload`
Envia um arquivo local para a máquina remota.
* **Parâmetros**:
  - `local_path` (string, obrigatório): Caminho do arquivo na máquina local.
  - `remote_path` (string, obrigatório): Destino final na máquina remota.

### 6. `download`
Baixa um arquivo da máquina remota para a máquina local.
* **Parâmetros**:
  - `remote_path` (string, obrigatório): Caminho do arquivo na máquina remota.
  - `local_path` (string, obrigatório): Destino final na máquina local.

### 7. `powershell_invoke`
Executa códigos e scripts PowerShell de forma direta, com suporte a remoting imediato.
* **Parâmetros**:
  - `command` (string, obrigatório): Código PowerShell a executar.
  - `computer_name` (string, opcional): Se fornecido, encapsula a execução dentro de um `Invoke-Command` para a máquina do domínio.
  - `timeout` (integer, opcional): Tempo limite.

---

## ⚡ Setup Rápido (Bootstrap no Windows)

### Passo 1: Preparar o Ambiente Virtual (.venv)
No PowerShell, navegue até a pasta `C:\ssh-mcp` e execute o script de provisionamento:
```powershell
powershell -ExecutionPolicy Bypass -File C:\ssh-mcp\scripts\setup.ps1
```
*Este utilitário baixa o `uv`, cria o ambiente virtual virtualizado em `server/.venv` e instala as dependências em altíssima velocidade.*

### Passo 2: Configurar o arquivo `.env`
Duplique o template de variáveis de ambiente:
```powershell
Copy-Item .env.example .env
```
Abra o `.env` e configure o modo padrão e o host de destino:
```env
CONNECTION_MODE=powershell
SSH_HOST=lab-mramos
# Dica: Deixe SSH_USERNAME e SSH_PASSWORD vazios para usar o Kerberos SSO do domínio!
```

### Passo 3: Executar Teste de Integridade Operacional
Garanta que todas as validações estão funcionais executando o quick-check:
```powershell
powershell -ExecutionPolicy Bypass -File C:\ssh-mcp\scripts\quick-check.ps1
```

---

## 🖥️ Integração com Claude Desktop

Para integrar este servidor de maneira transparente ao seu cliente de IA oficial, insira a configuração abaixo no seu arquivo `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ssh-powershell-mcp": {
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

## 🛡️ Estratégia de Segurança Corporativa

Este MCP foi desenvolvido sob diretrizes rígidas de segurança para ambientes enterprise:
1. **Isolamento de Credenciais (Zero Secret Leak)**: Variáveis sensíveis e chaves RSA ficam restritas ao arquivo local `.env`, o qual é protegido no git via regras rígidas no `.gitignore`.
2. **Prevenção de Shell Injections**: Ao utilizar `powershell.exe -EncodedCommand` e subprocessos isolados em Python, bloqueia-se qualquer tentativa de inserção de comandos maliciosos nas variáveis dinâmicas.
3. **Ofuscação de Auditoria**: Logs operacionais gravados em `logs/ssh-mcp.log` limpam senhas de conexões em texto plano, substituindo-as por máscaras de segurança (`<HIDDEN>`).

---

## 🧪 Validação da Suíte de Testes

O projeto conta com testes unitários, testes de protocolo stdio (JSON-RPC) e testes especializados para o motor PowerShell:

```powershell
# Validar motor PowerShell & Handlers do MCP
C:\ssh-mcp\server\.venv\Scripts\python.exe C:\ssh-mcp\tests\test_powershell.py

# Validar Handlers SSH
C:\ssh-mcp\server\.venv\Scripts\python.exe C:\ssh-mcp\tests\test_mcp_direct.py

# Validar handshakes JSON-RPC Stdio do MCP
C:\ssh-mcp\server\.venv\Scripts\python.exe C:\ssh-mcp\tests\test_mcp_protocol.py
```

---

## 🔍 Matriz de Resolução de Problemas (Troubleshooting)

| Sintoma | Causa Provável | Ação Corretiva Recomendada |
| :--- | :--- | :--- |
| **`WinRM cannot complete the operation...`** | O serviço WinRM não está habilitado ou o host não está na lista TrustedHosts. | Rode no PowerShell do servidor alvo: `Enable-PSRemoting -Force`. Se necessário, configure TrustedHosts: `Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*"` |
| **`Access is denied` no Invoke-Command** | Seu usuário local atual não tem privilégios administrativos na máquina alvo. | Forneça credenciais explícitas configurando `SSH_USERNAME` e `SSH_PASSWORD` no `.env` ou passando no comando `connect`. |
| **Saídas CLIXML aparecendo no console** | O PowerShell remote emitiu informações de depuração/carregamento de módulos. | Resolvido nativamente pelo servidor filtrando `#< CLIXML`. Certifique-se de que a versão do seu `server.py` está atualizada. |

---
*Desenvolvido e mantido pela equipe de Engenharia de Plataforma. Licenciado sob os termos da licença [MIT](LICENSE).*
