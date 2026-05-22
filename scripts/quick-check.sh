#!/bin/bash
# Script de Verificação Rápida - SSH-Connect MCP Server (Ambiente Linux/WSL)
# Uso: ./scripts/quick-check.sh

# Cores para output
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
GRAY='\033[0;90m'
NC='\033[0m' # Sem Cor

TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_WARNINGS=0

run_test() {
    local name="$1"
    local check_cmd="$2"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    if eval "$check_cmd" >/dev/null 2>&1; then
        echo -e "  ${GREEN}[OK]${NC} $name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        # Se falhou, vamos verificar se é falha crítica ou apenas um aviso
        if [[ "$name" == *"Config"* || "$name" == *"Atalho"* || "$name" == *"alcancável"* ]]; then
            echo -e "  ${YELLOW}[AVISO]${NC} $name"
            TESTS_WARNINGS=$((TESTS_WARNINGS + 1))
            return 1
        else
            echo -e "  ${RED}[FALHA]${NC} $name"
            TESTS_FAILED=$((TESTS_FAILED + 1))
            return 2
        fi
    fi
}

echo ""
echo -e "${CYAN}+----------------------------------------------------------------+${NC}"
echo -e "${CYAN}|         SSH-Connect MCP Server - Verificação Rápida             |${NC}"
echo -e "${CYAN}|                   Status & Health Check (Linux/WSL)            |${NC}"
echo -e "${CYAN}+----------------------------------------------------------------+${NC}"
echo ""

# Obter diretório absoluto do projeto
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${YELLOW}CATEGORIA 1: Estrutura de Arquivos${NC}"
echo -e "${GRAY}------------------------------------${NC}"
run_test "Diretório principal" "[ -d '$PROJECT_ROOT' ]"
run_test "Diretório do Servidor" "[ -d '$PROJECT_ROOT/server' ]"
run_test "Código Python" "[ -d '$PROJECT_ROOT/server/src/ssh_connect' ]"
run_test "pyproject.toml" "[ -f '$PROJECT_ROOT/server/pyproject.toml' ]"
run_test "Diretório de Logs" "[ -d '$PROJECT_ROOT/logs' ]"
run_test "Diretório de Scripts" "[ -d '$PROJECT_ROOT/scripts' ]"
run_test "Diretório de Config" "[ -d '$PROJECT_ROOT/config' ]"
run_test "Diretório de Testes" "[ -d '$PROJECT_ROOT/tests' ]"
run_test "Arquivo .env" "[ -f '$PROJECT_ROOT/.env' ]"
echo ""

echo -e "${YELLOW}CATEGORIA 2: Configuração MCP no Cliente${NC}"
echo -e "${GRAY}------------------------------------${NC}"
GEMINI_CONFIG_DIR="$HOME/.gemini/config"
GEMINI_CONFIG_FILE="$GEMINI_CONFIG_DIR/mcp_config.json"

run_test "Diretório .gemini/config existe" "[ -d '$GEMINI_CONFIG_DIR' ]"
run_test "mcp_config.json em .gemini/config" "[ -f '$GEMINI_CONFIG_FILE' ]"
run_test "MCP contém ssh-connect" "grep -q 'ssh-connect' '$GEMINI_CONFIG_FILE'"
run_test "Configuração aponta para .venv/bin" "grep -q '\.venv/bin/ssh-connect' '$GEMINI_CONFIG_FILE' || grep -q '\.venv/bin/python' '$GEMINI_CONFIG_FILE' || grep -q '\.venv/Scripts/ssh-connect' '$GEMINI_CONFIG_FILE' || grep -q '\.venv/Scripts/python' '$GEMINI_CONFIG_FILE'"
echo ""

echo -e "${YELLOW}CATEGORIA 3: Logs e Inicialização${NC}"
echo -e "${GRAY}------------------------------------${NC}"
run_test "Script setup.sh" "[ -f '$PROJECT_ROOT/scripts/setup.sh' ]"
run_test "Log de inicialização existe" "[ -f '$PROJECT_ROOT/logs/ssh-mcp.log' ]"
echo ""

echo -e "${YELLOW}CATEGORIA 4: Binários e Dependências${NC}"
echo -e "${GRAY}------------------------------------${NC}"
run_test "Python 3 no PATH" "command -v python3"
run_test "uv.lock sincronizado" "[ -f '$PROJECT_ROOT/server/uv.lock' ]"
run_test ".venv Python executável existe" "[ -x '$PROJECT_ROOT/server/.venv/bin/python' ]"
echo ""

echo -e "${YELLOW}CATEGORIA 5: Conectividade (usando .env)${NC}"
echo -e "${GRAY}------------------------------------${NC}"

# Carregar .env
SSH_HOST=""
SSH_PORT=22
if [ -f "$PROJECT_ROOT/.env" ]; then
    # Ler variáveis sem importar de forma insegura
    SSH_HOST=$(grep -v '^#' "$PROJECT_ROOT/.env" | grep 'SSH_HOST=' | cut -d'=' -f2- | tr -d '"'\''')
    PORT_VAL=$(grep -v '^#' "$PROJECT_ROOT/.env" | grep 'SSH_PORT=' | cut -d'=' -f2- | tr -d '"'\''')
    if [ ! -z "$PORT_VAL" ]; then
        SSH_PORT=$PORT_VAL
    fi
fi

if [ -z "$SSH_HOST" ]; then
    echo -e "  ${YELLOW}[AVISO]${NC} SSH_HOST não configurado no .env"
    TESTS_WARNINGS=$((TESTS_WARNINGS + 1))
else
    # Testar se a porta SSH está aberta usando timeout e bash tcp/netcat
    run_test "Host SSH ($SSH_HOST:$SSH_PORT) alcançável" "timeout 3 bash -c '</dev/tcp/$SSH_HOST/$SSH_PORT' || nc -z -w 3 '$SSH_HOST' '$SSH_PORT'"
fi
echo ""

echo -e "${YELLOW}RESUMO DOS TESTES${NC}"
echo -e "${GRAY}------------------------------------${NC}"
echo -e "  Total de Testes: ${CYAN}$TESTS_TOTAL${NC}"
echo -e "  Aprovados: ${GREEN}$TESTS_PASSED${NC}"
echo -e "  Falhas: ${RED}$TESTS_FAILED${NC}"
echo -e "  Avisos: ${YELLOW}$TESTS_WARNINGS${NC}"
echo ""

if [ "$TESTS_FAILED" -eq 0 ] && [ "$TESTS_WARNINGS" -le 2 ]; then
    echo -e "  STATUS FINAL: ${GREEN}[OK] SISTEMA SAUDÁVEL${NC}"
elif [ "$TESTS_FAILED" -eq 0 ]; then
    echo -e "  STATUS FINAL: ${YELLOW}[AVISO] SISTEMA OPERACIONAL (com avisos)${NC}"
else
    echo -e "  STATUS FINAL: ${RED}[ERRO] FALHAS DETECTADAS${NC}"
fi
echo ""
