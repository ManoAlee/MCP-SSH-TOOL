#!/bin/bash
# Script de Configuração e Transição do SSH-Connect MCP Server para Linux e WSL
# Uso: ./scripts/setup.sh

set -e

# Cores para output
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # Sem Cor

echo -e "${CYAN}=== INICIANDO CONFIGURAÇÃO DO SSH-CONNECT MCP SERVER (LINUX/WSL) ===${NC}"

# 1. Parar processos ativos que possam travar o servidor
echo -e "\n${YELLOW}[Passo 1] Procurando e encerrando instâncias ativas do servidor SSH-MCP...${NC}"
ACTIVE_PIDS=$(pgrep -f "ssh-connect" || true)
if [ ! -z "$ACTIVE_PIDS" ]; then
    echo "Encerrando processos ativos com PIDs: $ACTIVE_PIDS"
    kill $ACTIVE_PIDS || true
    sleep 1
fi

# 2. Garantir a estrutura de diretórios
echo -e "\n${YELLOW}[Passo 2] Verificando estrutura de diretórios...${NC}"
DIRS=(
    "config"
    "docs"
    "logs"
    "scripts"
    "tests"
)
for dir in "${DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo -e "  ${GREEN}[OK] Criado: $dir${NC}"
    else
        echo -e "  [OK] Já existe: $dir"
    fi
done

# 3. Verificar dependências globais (Python)
echo -e "\n${YELLOW}[Passo 3] Verificando interpretador Python 3...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Erro: python3 não está instalado ou não foi encontrado no PATH.${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo -e "  ${GREEN}[OK] Encontrado: $PYTHON_VERSION${NC}"

# 4. Criar/Reconstruir Ambiente Virtual (.venv)
echo -e "\n${YELLOW}[Passo 4] Configurando o ambiente virtual Python (.venv)...${NC}"
cd server

# Verificar se existe .venv do Windows (com a pasta Scripts)
if [ -d ".venv" ]; then
    if [ -d ".venv/Scripts" ] || [ ! -d ".venv/bin" ]; then
        echo -e "${YELLOW}Aviso: Detectado ambiente virtual de Windows em server/.venv. Removendo para recriar no Linux...${NC}"
        rm -rf .venv
    fi
fi

# Detectar se o uv está instalado
USE_UV=false
if command -v uv &> /dev/null; then
    USE_UV=true
    echo -e "  ${GREEN}[OK] uv detectado. Usando uv para velocidade máxima!${NC}"
else
    echo -e "  ${YELLOW}uv não encontrado. Utilizando python3 -m venv e pip padrão...${NC}"
fi

if [ "$USE_UV" = true ]; then
    uv venv .venv
    echo -e "${YELLOW}Instalando dependências e o pacote do servidor em modo editável com uv...${NC}"
    uv pip install -e .
else
    python3 -m venv .venv
    echo -e "${YELLOW}Instalando dependências e o pacote do servidor em modo editável com pip...${NC}"
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -e .
fi

cd ..
echo -e "  ${GREEN}[OK] Ambiente virtual (.venv) configurado com sucesso!${NC}"

# 5. Configurar arquivo de configuração MCP local
echo -e "\n${YELLOW}[Passo 5] Instalando configurações MCP locais...${NC}"
# Criar ou garantir que o arquivo .env existe a partir do .env.example se não existir
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "  ${GREEN}[OK] Criado arquivo .env a partir de .env.example. Por favor configure suas credenciais. ${NC}"
    else
        echo -e "  ${YELLOW}Aviso: .env.example não encontrado. Crie o arquivo .env manualmente.${NC}"
    fi
else
    echo -e "  [OK] Arquivo .env já existe."
fi

# 6. Executar validação de integridade rápida
echo -e "\n${YELLOW}[Passo 6] Executando diagnóstico inicial...${NC}"
if [ -f "./scripts/quick-check.sh" ]; then
    chmod +x ./scripts/quick-check.sh
    ./scripts/quick-check.sh
else
    echo -e "  ${YELLOW}Aviso: scripts/quick-check.sh não encontrado ou ainda não criado.${NC}"
fi

echo -e "\n${GREEN}=== CONFIGURAÇÃO PARA LINUX/WSL CONCLUÍDA COM SUCESSO ===${NC}"
