# 📘 Arquitetura e Implementação de PowerShell/WinRM Remoting

Este documento serve como a documentação técnica oficial das modificações e melhorias introduzidas no servidor **MCP SSH & PowerShell** para viabilizar o suporte nativo a remoting do Windows (PowerShell/WinRM) em infraestruturas Active Directory corporativas.

---

## 1. Contexto e Motivação

Originalmente, o servidor MCP atuava estritamente como um wrapper sobre conexões SSH e SFTP. Contudo, em ambientes baseados em Windows Server e domínios Active Directory (como a máquina `lab-mramos`), a melhor prática recomendada é a utilização nativa de **WinRM (Windows Remote Management)** e PowerShell. 

A inclusão do suporte a PowerShell permite:
* Adoção de **Single Sign-On (SSO)** com Kerberos, herdando as credenciais locais do operador sem precisar expor senhas em texto plano.
* Execução e listagem fiel de objetos de sistema via PowerShell.
* Transferência de arquivos simplificada sem a necessidade de expor compartilhamentos de arquivos de rede SMB inseguros.

---

## 2. Visão Geral da Arquitetura

O servidor MCP agora é híbrido. Dependendo da configuração ativa em `.env` ou dos argumentos da ferramenta `connect`, ele chaveia a execução interna entre duas engines isoladas:

```text
               +-----------------------+
               |  JSON-RPC MCP Client  |
               +-----------+-----------+
                           |
                           v
               +-----------+-----------+
               |   server.py (MCP)     |
               +-----+-----------+-----+
                     |           |
       [modo ssh]    |           |    [modo powershell]
                     v           v
           +---------+--+     +--+---------+
           |  Paramiko  |     | PowerShell |
           +---------+--+     +--+---------+
                     |           |
             (SSH / SFTP)      (WinRM / SSO)
                     |           |
                     v           v
           +---------+--+     +--+---------+
           | Linux Host |     | Win Host   |
           +------------+     +------------+
```

---

## 3. Detalhes de Implementação Sênior

### A. Prevenção de Shell Injections via `-EncodedCommand`
Toda execução remota ou local do PowerShell é despachada utilizando o executável nativo `powershell.exe` configurado com o argumento `-EncodedCommand`. 
* **Fluxo**:
  1. O comando é composto no Python em formato de string Unicode UTF-8.
  2. Ele é re-codificado para `UTF-16LE` (o formato padrão de strings do Windows).
  3. A string binária resultante é convertida para `Base64` e decodificada como string ASCII simples.
  4. O Python executa o comando `powershell.exe -EncodedCommand <BASE64>`.
* **Benefício**: Previne por completo qualquer quebra de strings, escape de aspas simples/duplas no shell ou injeção de parâmetros maliciosos.

### B. Mapeamento de Ferramentas Híbridas
1. **`connect`**: Valida a conexão remota disparando um teste leve (`Test-WSMan`) no host fornecido. Se credenciais forem configuradas, cria um objeto seguro do tipo `[PSCredential]` em tempo de execução.
2. **`execute`**: Executa o script envelopado em um bloco `Invoke-Command -ComputerName <HOST>`.
3. **`list_files`**: Executa remotamente a listagem de arquivos e pastas via PowerShell e serializa o resultado em JSON utilizando `ConvertTo-Json -Compress`. O Python decodifica essa string JSON, garantindo precisão absoluta de tamanho de arquivos e metadados.
4. **`upload`/`download`**: Abre uma sessão WinRM temporária persistida em variável `$sess = New-PSSession -ComputerName <HOST>`. Utiliza `Copy-Item -ToSession $sess` (para uploads) e `Copy-Item -FromSession $sess` (para downloads).

### C. Limpeza de Outputs (Streams de Depuração)
* Adicionado `$ProgressPreference = 'SilentlyContinue'` em todas as chamadas PowerShell para suprimir barras de progresso que sujam a saída de console.
* Filtragem automática de strings começadas com `#< CLIXML` (geradas por streams de depuração do PowerShell remoting).

---

## 4. Estrutura de Arquivos Criados/Modificados

### Modificados
* **`server/src/ssh_connect/server.py`**:
  * Adicionado estado de sessão PowerShell (`ps_host`, `ps_username`, `ps_password`, `connection_mode`).
  * Implementação da rotina assíncrona `run_powershell_async`.
  * Redirecionamento condicional de `handle_connect`, `handle_execute`, `handle_list_files`, `handle_upload`, e `handle_download`.
  * Registro da nova ferramenta `powershell_invoke`.
* **`.env.example`** & **`README.md`**:
  * Atualização de templates e documentação completa com diagramas de fluxo de dados.

### Novos
* **`tests/test_powershell.py`**:
  * Testes automatizados unitários para verificar escape de strings, codificação UTF-16LE, conversões de JSON e handlers MCP.
* **`tests/test_live.py`**:
  * Script de teste rápido que executa uma validação real em ambiente de produção contra a máquina `lab-mramos` no Active Directory local.

---

## 5. Como Executar e Validar

### Executar a Suite de Testes Completa
```powershell
# Testes do Motor PowerShell
C:\ssh-mcp\server\.venv\Scripts\python.exe C:\ssh-mcp\tests\test_powershell.py

# Testes de Regressão SSH
C:\ssh-mcp\server\.venv\Scripts\python.exe C:\ssh-mcp\tests\test_mcp_direct.py
```

### Executar Teste ao Vivo contra `lab-mramos`
```powershell
C:\ssh-mcp\server\.venv\Scripts\python.exe C:\ssh-mcp\tests\test_live.py
```

---
*Documentação oficial de engenharia de infraestrutura da Automotion.*
