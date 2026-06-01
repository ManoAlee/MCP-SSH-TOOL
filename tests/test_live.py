import asyncio
import sys
import os

# Setup path dynamically to import the module
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, os.path.join(project_root, "server", "src"))

from ssh_connect import server

async def main():
    print("Iniciando teste de conexao ao lab-mramos via PowerShell...")
    try:
        # Tenta conectar via powershell
        res = await server.handle_connect({"host": "lab-mramos", "mode": "powershell"})
        print(f"[OK] Conectado com sucesso: {res[0].text}")
        
        # Tenta executar o comando solicitado pelo usuario
        cmd = "Get-ChildItem -Path 'D:\\SoMachine Software\\Configuration'"
        print(f"Executando comando: {cmd}")
        res_exec = await server.handle_execute({"command": cmd})
        print("[OK] Comando executado! Resultado:")
        print(res_exec[0].text)
        
        # Testar desconectar
        res_dis = await server.handle_disconnect()
        print(f"[OK] Desconectado: {res_dis[0].text}")
        
    except Exception as e:
        print(f"[FALHA] Ocorreu um erro no teste: {str(e)}")

if __name__ == '__main__':
    asyncio.run(main())
