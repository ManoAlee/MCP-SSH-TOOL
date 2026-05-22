# SSH-Connect MCP Server - Documentação Completa

## 📚 Índice de Conteúdo

1. [README](#readme)
2. [Guia de Instalação](#guia-de-instalação)
3. [Guia de Uso](#guia-de-uso)
4. [Referência de API](#referência-de-api)
5. [Arquitetura do Sistema](#arquitetura-do-sistema)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)
8. [Manutenção](#manutenção)

---

## README

### Sobre o SSH-Connect MCP Server

**SSH-Connect MCP Server** é um servidor Model Context Protocol (MCP) que permite integração segura com servidores SSH através do Antigravity e VS Code.

### Características Principais

- ✅ **Conexão SSH Automática** - Conecta-se ao servidor configurado automaticamente
- ✅ **Inicialização Automática** - Inicia na boot do PC
- ✅ **Execução de Comandos** - Execute comandos remotos via MCP
- ✅ **Transferência de Arquivos** - Upload/download de arquivos
- ✅ **Listagem de Diretórios** - Navegue estrutura remota
- ✅ **Logging Completo** - Registra todas as operações
- ✅ **Seguro** - Credenciais protegidas e comunicação criptografada

### Requisitos do Sistema

- **Windows 10/11**
- **Python 3.12+** (via uv)
- **uv 0.11.15+** (gerenciador de pacotes)
- **Antigravity ou VS Code** (cliente MCP)
- **Acesso SSH** ao servidor remoto

### Status de Produção

✅ **PRONTO PARA PRODUÇÃO**
- Todas as validações técnicas concluídas
- Testes de conectividade aprovados
- Documentação completa
- Sistema de logging ativo

---

## Guia de Instalação

### Pré-requisitos

1. Clone ou tenha o repositório em: `C:\ssh-mcp\ssh-connect-mcp-server`
2. Instale `uv`: https://astral.sh/uv

### Passos de Instalação

#### 1. Baixar o Repositório
```powershell
git clone https://github.com/t-suganuma/ssh-connect-mcp-server.git C:\ssh-mcp\ssh-connect-mcp-server
cd C:\ssh-mcp\ssh-connect-mcp-server
```

#### 2. Instalar uv
```powershell
powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
```

#### 3. Configurar Credenciais SSH

Edite: `C:\Users\seu_usuario\.gemini\config\mcp_config.json`

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
        "SSH_HOST": "seu_host",
        "SSH_PORT": "22",
        "SSH_USERNAME": "seu_usuario",
        "SSH_PASSWORD": "sua_senha",
        "PATH": "C:\\Users\\seu_usuario\\.local\\bin;C:\\Windows\\System32;C:\\Windows"
      }
    }
  }
}
```

#### 4. Configurar Inicialização Automática

Execute como Administrator:
```powershell
powershell -ExecutionPolicy Bypass -File "C:\ssh-mcp\Register-StartupTask.ps1"
```

Ou copie o atalho manualmente:
```
Copy: C:\ssh-mcp\StartSSHMCP.bat
To: %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\SSH-Connect-MCP.lnk
```

#### 5. Teste

```powershell
# Verificar se está funcionando
Get-Content "C:\ssh-mcp\ssh-mcp.log" -Tail 5

# Testar no Antigravity
use_mcp_tool(server_name="ssh-connect", tool_name="connect", arguments={})
```

---

## Guia de Uso

### No Antigravity

#### Conectar ao Servidor SSH
```
use_mcp_tool(server_name="ssh-connect", tool_name="connect", arguments={})
```

**Resposta esperada:**
```
Connected to username@host:22
```

#### Executar Comando
```
use_mcp_tool(server_name="ssh-connect", tool_name="execute", arguments={"command": "ls -la"})
```

#### Listar Arquivos
```
use_mcp_tool(server_name="ssh-connect", tool_name="list_files", arguments={"path": "/home/usuario"})
```

#### Upload de Arquivo
```
use_mcp_tool(server_name="ssh-connect", tool_name="upload", arguments={
  "local_path": "C:\\arquivo.txt",
  "remote_path": "/home/usuario/arquivo.txt"
})
```

#### Download de Arquivo
```
use_mcp_tool(server_name="ssh-connect", tool_name="download", arguments={
  "remote_path": "/home/usuario/arquivo.txt",
  "local_path": "C:\\arquivo.txt"
})
```

#### Desconectar
```
use_mcp_tool(server_name="ssh-connect", tool_name="disconnect", arguments={})
```

### No VS Code

1. Abra VS Code
2. Vá para a aba Copilot Chat
3. Ative o servidor MCP em configurações
4. Use os comandos acima normalmente

---

## Referência de API

### Ferramentas Disponíveis

#### 1. connect
Conecta ao servidor SSH configurado.

**Argumentos:**
- `host` (opcional): Sobrescreve SSH_HOST
- `port` (opcional): Sobrescreve SSH_PORT (padrão: 22)
- `username` (opcional): Sobrescreve SSH_USERNAME
- `password` (opcional): Sobrescreve SSH_PASSWORD
- `key_path` (opcional): Caminho para chave privada SSH

**Exemplo:**
```json
{
  "host": "10.0.0.7",
  "port": 22,
  "username": "user",
  "password": "pass"
}
```

**Retorno:**
```
Connected to user@10.0.0.7:22
```

---

#### 2. disconnect
Desconecta do servidor SSH.

**Argumentos:** Nenhum

**Retorno:**
```
Disconnected from SSH server
```

---

#### 3. execute
Executa comando no servidor remoto.

**Argumentos:**
- `command` (obrigatório): Comando a executar
- `timeout` (opcional): Timeout em segundos (padrão: 60)

**Exemplo:**
```json
{
  "command": "cat /etc/os-release",
  "timeout": 30
}
```

**Retorno:**
```
Command: cat /etc/os-release
Exit status: 0

STDOUT:
NAME="Ubuntu"
VERSION="20.04.6 LTS"
```

---

#### 4. upload
Faz upload de arquivo para o servidor.

**Argumentos:**
- `local_path` (obrigatório): Caminho local do arquivo
- `remote_path` (obrigatório): Caminho remoto

**Exemplo:**
```json
{
  "local_path": "C:\\dados.txt",
  "remote_path": "/home/user/dados.txt"
}
```

**Retorno:**
```
Uploaded C:\dados.txt to /home/user/dados.txt
```

---

#### 5. download
Faz download de arquivo do servidor.

**Argumentos:**
- `remote_path` (obrigatório): Caminho remoto
- `local_path` (obrigatório): Caminho local

**Exemplo:**
```json
{
  "remote_path": "/var/log/app.log",
  "local_path": "C:\\app.log"
}
```

**Retorno:**
```
Downloaded /var/log/app.log to C:\app.log
```

---

#### 6. list_files
Lista arquivos em diretório remoto.

**Argumentos:**
- `path` (obrigatório): Caminho do diretório

**Exemplo:**
```json
{
  "path": "/home/user"
}
```

**Retorno:**
```
Files in /home/user:
arquivo.txt (file, 1024 bytes)
pasta (directory, 0 bytes)
script.sh (file, 512 bytes)
```

---

## Arquitetura do Sistema

### Estrutura de Diretórios

```
C:\ssh-mcp\
├── ssh-connect-mcp-server/              # Repositório MCP
│   ├── src/ssh_connect/
│   │   ├── __init__.py                  # Ponto de entrada
│   │   └── server.py                    # Implementação do servidor
│   ├── pyproject.toml                   # Configuração do projeto
│   ├── uv.lock                          # Lock de dependências
│   └── ...
│
├── StartSSHMCP.bat                      # Script de inicialização
├── Start-SSHMCPServer.ps1              # Alternativa PowerShell
├── Register-StartupTask.ps1            # Registro de tarefa
├── quick-check.ps1                     # Verificação rápida
├── test_ssh_direct.py                  # Teste SSH
├── VALIDATION_REPORT.md                # Relatório técnico
├── VALIDATION_SUMMARY.md               # Resumo executivo
├── SETUP_COMPLETE.md                   # Guia de setup
├── ssh-mcp.log                         # Arquivo de log
└── ssh-mcp.pid                         # ID do processo

%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\
└── SSH-Connect-MCP.lnk                 # Atalho de inicialização

.gemini\config\
└── mcp_config.json                     # Configuração principal (redundante)

.gemini\antigravity\
└── mcp_config.json                     # Configuração Antigravity

AppData\Roaming\Antigravity\
└── config.json                         # Configuração Antigravity alt.
```

### Fluxo de Inicialização

```
1. PC Liga
   ↓
2. Windows Executa Startup Folder
   ↓
3. Atalho SSH-Connect-MCP.lnk é acionado
   ↓
4. StartSSHMCP.bat é executado
   ↓
5. uv.exe é localizado no PATH
   ↓
6. Servidor ssh-connect inicia
   ↓
7. Escuta stdin/stdout (protocolo MCP)
   ↓
8. Aguarda conexão do cliente (Antigravity/VS Code)
```

### Fluxo de Conexão SSH

```
Cliente (Antigravity)
   ↓
   use_mcp_tool(server_name="ssh-connect", tool_name="connect")
   ↓
MCP Server
   ↓
   paramiko.SSHClient.connect()
   ↓
SSH Server (10.0.0.7:22)
   ↓
   Credenciais validadas
   ↓
   Conexão estabelecida
   ↓
Retorna ao Cliente: "Connected to user@host:22"
```

### Componentes Principais

#### 1. **server.py**
- Implementação do servidor MCP
- Gerenciamento de conexões SSH
- Manipulação de arquivos (SFTP)
- Tratamento de erros

#### 2. **paramiko**
- Biblioteca SSH para Python
- Suporta autenticação por senha e chave
- Gerenciamento de SFTP
- 221.97 KiB de dependências

#### 3. **mcp (Model Context Protocol)**
- Framework para comunicação entre cliente e servidor
- Protocolo JSON-RPC
- stdio transport
- 74.29 KiB de dependências

#### 4. **uv**
- Gerenciador de pacotes Python moderno
- Instalação rápida de dependências
- Lock file para reproducibilidade

---

## Troubleshooting

### Problema: "Erro spawn uv ENOENT"

**Causa:** uv não encontrado no PATH

**Solução:**
1. Edite `mcp_config.json`
2. Altere:
   ```json
   "command": "uv"
   ```
   Para:
   ```json
   "command": "C:\\Users\\seu_usuario\\.local\\bin\\uv.exe"
   ```
3. Reinicie o Antigravity

---

### Problema: Servidor não inicia

**Verificação:**
```powershell
# 1. Verificar log
Get-Content "C:\ssh-mcp\ssh-mcp.log"

# 2. Teste manual
$env:Path = "C:\Users\seu_usuario\.local\bin;$env:Path"
cd C:\ssh-mcp\ssh-connect-mcp-server
uv run ssh-connect

# 3. Verificar se uv existe
Test-Path "C:\Users\seu_usuario\.local\bin\uv.exe"
```

---

### Problema: Falha na autenticação SSH

**Verificação:**
1. Teste credenciais manualmente:
   ```powershell
   $env:Path = "C:\Users\seu_usuario\.local\bin;$env:Path"
   cd C:\ssh-mcp\ssh-connect-mcp-server
   uv run python C:\ssh-mcp\test_ssh_direct.py
   ```

2. Verificar arquivo de configuração:
   ```powershell
   Get-Content "C:\Users\seu_usuario\.gemini\config\mcp_config.json" | ConvertFrom-Json
   ```

3. Confirmar credenciais:
   - Host: 10.0.0.7
   - Porta: 22
   - Usuário: correto
   - Senha: correta (sem espaços extras)

---

### Problema: Comando não encontrado no Antigravity

**Solução:**
1. Reinicie o Antigravity completamente
2. Aguarde 5-10 segundos
3. Tente novamente

---

### Problema: Conexão SSH muito lenta

**Causa:** Latência de rede ou problema com servidor

**Solução:**
```powershell
# Testar conectividade
Test-NetConnection -ComputerName "10.0.0.7" -Port 22

# Testar ping
ping 10.0.0.7

# Aumentar timeout
# Edite o comando para incluir timeout maior
```

---

### Problema: Arquivo de log muito grande

**Solução:**
```powershell
# Limpar log antigo
Clear-Content "C:\ssh-mcp\ssh-mcp.log"

# Ou rotacionar
Move-Item "C:\ssh-mcp\ssh-mcp.log" "C:\ssh-mcp\ssh-mcp.log.old"
```

---

## FAQ

### P: Como altero o servidor SSH?
**R:** Edite `mcp_config.json` e altere `SSH_HOST`, `SSH_PORT`, etc.

### P: Posso usar chave SSH em vez de senha?
**R:** Sim! Defina `SSH_KEY_PATH` e `SSH_KEY_PASSPHRASE` em vez de `SSH_PASSWORD`.

### P: Posso executar múltiplas conexões?
**R:** Não. Uma conexão por vez. Use `disconnect` para alternar.

### P: Os arquivos de log ficam muito grandes?
**R:** Sim. Limpe periodicamente ou implemente rotação de logs.

### P: Posso iniciar manualmente?
**R:** Sim: `C:\ssh-mcp\StartSSHMCP.bat`

### P: Como desabilitar inicialização automática?
**R:** Remova o atalho de Startup ou execute o script de desregistry.

### P: Como atualizar o servidor?
**R:** 
```powershell
cd C:\ssh-mcp\ssh-connect-mcp-server
git pull
uv lock --upgrade
```

### P: Preciso de privilégios especiais?
**R:** Não para o usuário normal. Apenas para registrar tarefa agendada.

### P: Posso usar em rede corporativa?
**R:** Sim, mas confirme credenciais SSH e firewall.

### P: Como monitoro o servidor?
**R:** 
```powershell
# Verificar processos
Get-Process | Where-Object {$_.ProcessName -like "*uv*"}

# Ver log em tempo real
Get-Content "C:\ssh-mcp\ssh-mcp.log" -Wait
```

---

## Manutenção

### Checklist Mensal

- [ ] Revisar arquivo de log para erros
- [ ] Validar conectividade SSH
- [ ] Limpar arquivo de log se necessário
- [ ] Verificar se processo está rodando

### Checklist Trimestral

- [ ] Atualizar uv: `powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"`
- [ ] Atualizar dependências: `uv lock --upgrade`
- [ ] Backup de configurações MCP
- [ ] Executar validação técnica completa

### Backup

**Arquivos importantes para backup:**
```
C:\Users\seu_usuario\.gemini\config\mcp_config.json
C:\ssh-mcp\ssh-connect-mcp-server\
C:\ssh-mcp\StartSSHMCP.bat
```

### Monitoramento

**Verificação rápida:**
```powershell
powershell -ExecutionPolicy Bypass -File "C:\ssh-mcp\quick-check.ps1"
```

**Validação completa:**
```powershell
Get-Content "C:\ssh-mcp\VALIDATION_REPORT.md"
```

---

## Suporte

### Documentação Adicional

- [VALIDATION_REPORT.md](VALIDATION_REPORT.md) - Relatório técnico detalhado
- [SETUP_COMPLETE.md](SETUP_COMPLETE.md) - Guia de setup passo a passo
- [VALIDATION_SUMMARY.md](VALIDATION_SUMMARY.md) - Resumo executivo

### Contato

Para problemas técnicos, consulte:
1. O arquivo de log: `C:\ssh-mcp\ssh-mcp.log`
2. Executar validação: `quick-check.ps1`
3. Testar SSH manualmente: `test_ssh_direct.py`

---

## Histórico de Versões

### v1.0.0 (21 de maio de 2026)
- ✅ Release inicial
- ✅ Suporte a SSH por senha
- ✅ Inicialização automática
- ✅ Logging completo
- ✅ Validação técnica aprovada
- ✅ Documentação completa

---

## Licença

Este projeto segue a mesma licença do repositório original:
https://github.com/t-suganuma/ssh-connect-mcp-server

---

**Última atualização:** 21 de maio de 2026  
**Status:** ✓ PRONTO PARA PRODUÇÃO  
**Validação:** COMPLETA
