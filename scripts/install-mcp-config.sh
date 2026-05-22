#!/bin/bash
# Script para instalar configurações MCP no Linux/WSL
# Uso: ./scripts/install-mcp-config.sh

set -e

# Cores para output
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # Sem Cor

echo -e "${CYAN}=== INSTALANDO CONFIGURAÇÕES MCP NO CLIENTE (LINUX/WSL) ===${NC}"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_CONFIG="$PROJECT_ROOT/config/mcp_config_linux.json"

TARGETS=(
    "$HOME/.gemini/config/mcp_config.json"
    "$HOME/.gemini/antigravity/mcp_config.json"
)

if [ ! -f "$SRC_CONFIG" ]; then
    echo -e "${RED}Erro: Arquivo de configuração de origem não encontrado em: $SRC_CONFIG${NC}"
    exit 1
fi

for target in "${TARGETS[@]}"; do
    target_dir=$(dirname "$target")
    
    # Criar diretório se não existir
    if [ ! -d "$target_dir" ]; then
        echo "Criando diretório: $target_dir"
        mkdir -p "$target_dir"
    fi
    
    # Fazer backup se o arquivo já existir
    if [ -f "$target" ]; then
        bak_file="${target}.bak.$(date +%Y%m%d%H%M%S)"
        cp "$target" "$bak_file"
        echo "Backup criado: $bak_file"
    fi
    
    # Copiar configuração
    cp "$SRC_CONFIG" "$target"
    echo -e "  ${GREEN}[OK] Copiado:${NC} $SRC_CONFIG -> $target"
done

echo -e "\n${GREEN}Instalação concluída! Por favor, reinicie seu cliente MCP (Cursor, Claude, Antigravity, etc.) para carregar as novas configurações.${NC}"
echo ""
