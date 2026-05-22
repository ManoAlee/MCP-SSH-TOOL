# Checklist de Operação - SSH-Connect MCP Server

## 📋 Checklist de Operação Diária

### ☑ Antes de Começar o Dia
- [ ] Verificar se o servidor MCP está rodando
  ```powershell
  Get-Process | Where-Object {$_.ProcessName -like "*uv*" -or $_.ProcessName -like "*python*"}
  ```
- [ ] Verificar se há erros no log
  ```powershell
  Get-Content "C:\ssh-mcp\ssh-mcp.log" -Tail 10
  ```
- [ ] Testar conectividade SSH
  ```powershell
  Test-NetConnection -ComputerName "10.0.0.7" -Port 22
  ```

### ☑ Durante o Dia
- [ ] Monitorar logs se enfrentar problemas
- [ ] Registrar qualquer comportamento anômalo
- [ ] Relatar erros

### ☑ Fim do Dia
- [ ] Verificar se há mais de 100 linhas no log (considerar limpeza)
  ```powershell
  (Get-Content "C:\ssh-mcp\ssh-mcp.log" | Measure-Object -Line).Lines
  ```

---

## 📋 Checklist Semanal

- [ ] Revisar arquivo de log (`ssh-mcp.log`)
- [ ] Verificar espaço em disco (arquivo de log pode crescer)
- [ ] Limpar log se necessário
  ```powershell
  Clear-Content "C:\ssh-mcp\ssh-mcp.log"
  ```
- [ ] Executar validação rápida
  ```powershell
  powershell -ExecutionPolicy Bypass -File "C:\ssh-mcp\quick-check.ps1"
  ```
- [ ] Testar todas as ferramentas (connect, execute, upload, download, list_files)
- [ ] Documentar qualquer problema encontrado

---

## 📋 Checklist Mensal

- [ ] Revisar log completo para padrões de erro
  ```powershell
  Get-Content "C:\ssh-mcp\ssh-mcp.log" | Select-String "Error|Warning|Failed"
  ```
- [ ] Fazer backup de configuração
  ```powershell
  Copy-Item "C:\Users\seu_usuario\.gemini\config\mcp_config.json" "C:\ssh-mcp\backup\mcp_config.json.$(Get-Date -Format 'yyyy-MM-dd')"
  ```
- [ ] Verificar espaço em disco
  ```powershell
  Get-Item "C:\ssh-mcp" | Select-Object @{Name="Size (MB)";Expression={[math]::Round(((Get-ChildItem $_.FullName -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB),2)}}
  ```
- [ ] Rotacionar arquivo de log (se > 100 MB)
  ```powershell
  Move-Item "C:\ssh-mcp\ssh-mcp.log" "C:\ssh-mcp\ssh-mcp.log.$(Get-Date -Format 'yyyy-MM-dd')"
  ```
- [ ] Testar recuperação de falhas
  ```powershell
  # Parar servidor
  Stop-Process -Name "*uv*" -Force
  
  # Aguardar 10 segundos
  Start-Sleep -Seconds 10
  
  # Verificar se reinicia automaticamente
  Get-Process | Where-Object {$_.ProcessName -like "*uv*"}
  ```

---

## 📋 Checklist Trimestral

- [ ] Atualizar uv
  ```powershell
  powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
  uv --version
  ```
- [ ] Atualizar dependências
  ```powershell
  cd C:\ssh-mcp\ssh-connect-mcp-server
  uv lock --upgrade
  ```
- [ ] Executar validação técnica completa
  ```powershell
  Get-Content "C:\ssh-mcp\VALIDATION_REPORT.md" | Out-Host -Paging
  ```
- [ ] Fazer backup completo
  ```powershell
  $backupDate = Get-Date -Format 'yyyy-MM-dd'
  New-Item -ItemType Directory "C:\ssh-mcp\backup\$backupDate" -Force
  Copy-Item "C:\ssh-mcp\ssh-connect-mcp-server" "C:\ssh-mcp\backup\$backupDate\" -Recurse
  Copy-Item "C:\Users\seu_usuario\.gemini\config\mcp_config.json" "C:\ssh-mcp\backup\$backupDate\"
  ```

---

## 🆘 Plano de Resposta a Incidentes

### Cenário 1: Servidor não inicia na boot

**Sintoma:** Log vazio ou não existe

**Passos de Resolução:**
1. [ ] Verificar se atalho existe
   ```powershell
   Test-Path "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\SSH-Connect-MCP.lnk"
   ```
2. [ ] Verificar se arquivo batch existe
   ```powershell
   Test-Path "C:\ssh-mcp\StartSSHMCP.bat"
   ```
3. [ ] Iniciar manualmente
   ```powershell
   C:\ssh-mcp\StartSSHMCP.bat
   ```
4. [ ] Recriador atalho se necessário
   ```powershell
   $batPath = "C:\ssh-mcp\StartSSHMCP.bat"
   $lnkPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\SSH-Connect-MCP.lnk"
   $shell = New-Object -ComObject WScript.Shell
   $shortcut = $shell.CreateShortcut($lnkPath)
   $shortcut.TargetPath = $batPath
   $shortcut.WindowStyle = 7
   $shortcut.Save()
   ```
5. [ ] Reiniciar PC

**Tempo estimado:** 5-10 minutos

---

### Cenário 2: Falha de autenticação SSH

**Sintoma:** Erro "Failed to connect" ao executar `connect`

**Passos de Resolução:**
1. [ ] Testar credenciais manualmente
   ```powershell
   cd C:\ssh-mcp\ssh-connect-mcp-server
   $env:Path = "C:\Users\seu_usuario\.local\bin;$env:Path"
   uv run python C:\ssh-mcp\test_ssh_direct.py
   ```
2. [ ] Verificar arquivo de configuração
   ```powershell
   Get-Content "C:\Users\seu_usuario\.gemini\config\mcp_config.json" | ConvertFrom-Json
   ```
3. [ ] Testar conectividade
   ```powershell
   Test-NetConnection -ComputerName "10.0.0.7" -Port 22
   ```
4. [ ] Atualizar credenciais se necessário
5. [ ] Reiniciar servidor

**Tempo estimado:** 10-15 minutos

---

### Cenário 3: Servidor não responsivo ("Erro spawn uv ENOENT")

**Sintoma:** VS Code/Antigravity não consegue iniciar o servidor

**Passos de Resolução:**
1. [ ] Verificar se uv está instalado
   ```powershell
   Test-Path "C:\Users\seu_usuario\.local\bin\uv.exe"
   ```
2. [ ] Reinstalar uv se necessário
   ```powershell
   powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
   ```
3. [ ] Atualizar caminho no `mcp_config.json`
   ```json
   "command": "C:\\Users\\seu_usuario\\.local\\bin\\uv.exe"
   ```
4. [ ] Reiniciar Antigravity/VS Code

**Tempo estimado:** 5-10 minutos

---

### Cenário 4: Consumo alto de espaço em disco

**Sintoma:** Log file com vários GBs

**Passos de Resolução:**
1. [ ] Verificar tamanho
   ```powershell
   Get-Item "C:\ssh-mcp\ssh-mcp.log" | Select-Object Length
   ```
2. [ ] Rotacionar arquivo antigo
   ```powershell
   Move-Item "C:\ssh-mcp\ssh-mcp.log" "C:\ssh-mcp\ssh-mcp.log.$(Get-Date -Format 'yyyy-MM-dd').backup"
   ```
3. [ ] Limpar log novo
   ```powershell
   Clear-Content "C:\ssh-mcp\ssh-mcp.log"
   ```

**Tempo estimado:** 2-3 minutos

---

## 📊 Métricas a Monitorar

### Performance
- [ ] Tempo de resposta do comando SSH (< 1 segundo esperado)
- [ ] Tempo de upload/download (depende do tamanho)
- [ ] Memória usada pelo processo uv (< 200 MB esperado)

### Confiabilidade
- [ ] Uptime do servidor (objetivo: > 99%)
- [ ] Taxa de erros (objetivo: < 1%)
- [ ] Tempo de recuperação de falhas (< 10 segundos)

### Segurança
- [ ] Tentativas falhadas de autenticação (monitorar padrões)
- [ ] Accesso a arquivos sensíveis (auditar)
- [ ] Credenciais expostas (verificar logs)

---

## 🔄 Procedimento de Reinicialização

### Parada Planejada
1. [ ] Notificar usuários com antecedência
2. [ ] Aguardar conclusão de operações em andamento
3. [ ] Parar servidor
   ```powershell
   Stop-Process -Name "*uv*" -Force
   ```
4. [ ] Verificar se parou
   ```powershell
   Get-Process | Where-Object {$_.ProcessName -like "*uv*"}
   ```
5. [ ] Fazer manutenção se necessário
6. [ ] Iniciar servidor manualmente ou reiniciar PC
   ```powershell
   C:\ssh-mcp\StartSSHMCP.bat
   ```
7. [ ] Notificar usuários que está de volta

### Parada de Emergência
1. [ ] Parar servidor imediatamente
   ```powershell
   Stop-Process -Name "*uv*" -Force -ErrorAction Continue
   Stop-Process -Name "*python*" -Force -ErrorAction Continue
   ```
2. [ ] Investigar causa do problema
3. [ ] Resolver problema
4. [ ] Reiniciar servidor

---

## 📞 Contatos e Escalação

### Nível 1 - Suporte Básico
- Verificar logs
- Executar quick-check.ps1
- Reiniciar servidor

### Nível 2 - Suporte Técnico
- Analisar VALIDATION_REPORT.md
- Executar troubleshooting detalhado
- Atualizar dependências

### Nível 3 - Escalação
- Consultar documentação completa
- Possível reimplementação do zero
- Contactar desenvolvedor original

---

## 📝 Registro de Incidentes

```
Data: ___________
Hora: ___________
Severidade: [ ] Baixa [ ] Média [ ] Alta [ ] Crítica
Tipo: [ ] Login [ ] Performance [ ] Conectividade [ ] Outro

Descrição:
_____________________________________________________________________________

Ações tomadas:
_____________________________________________________________________________

Resultado:
_____________________________________________________________________________

Tempo de resolução: _______ minutos
```

---

## ✅ Checklist de Preparação para Produção

Antes de considerar o sistema "em produção":

- [ ] Todas as validações técnicas aprovadas
- [ ] Testes de conectividade bem-sucedidos
- [ ] Backup de configuração realizado
- [ ] Documentação revisada
- [ ] Plano de resposta a incidentes criado
- [ ] Responsável designado
- [ ] Contatos de suporte documentados
- [ ] Métricas de monitoramento definidas
- [ ] Processo de manutenção estabelecido
- [ ] Treinamento de usuários concluído

---

**Última atualização:** 21 de maio de 2026  
**Versão:** 1.0.0  
**Status:** ✓ PRONTO PARA OPERAÇÃO
