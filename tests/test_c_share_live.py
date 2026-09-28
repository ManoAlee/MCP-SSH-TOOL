import asyncio
import sys
import os

# Setup path dynamically to import the module
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, os.path.join(project_root, "server", "src"))

from ssh_connect import server

async def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
    print("Iniciando validação do mecanismo C$ para upload/download...")
    local_file = os.path.join(project_root, "tests", "test_upload_src.txt")
    remote_file = "C:\\temp\\test_upload_dest.txt"
    
    # Criar arquivo local temporário
    with open(local_file, "w", encoding="utf-8") as f:
        f.write("Teste de transferência direta via compartilhamento C$ - MCP")
        
    try:
        # Conectar ao host remote-host-01
        res_conn = await server.handle_connect({"host": "remote-host-01", "mode": "powershell"})
        print(f"[OK] {res_conn[0].text}")
        
        # Executar upload
        print(f"Enviando {local_file} para {remote_file}...")
        res_up = await server.handle_upload({"local_path": local_file, "remote_path": remote_file})
        print(f"[OK] {res_up[0].text}")
        
        # Baixar de volta com outro nome para validar
        local_file_back = os.path.join(project_root, "tests", "test_upload_back.txt")
        print(f"Baixando de volta {remote_file} para {local_file_back}...")
        res_down = await server.handle_download({"remote_path": remote_file, "local_path": local_file_back})
        print(f"[OK] {res_down[0].text}")
        
        # Verificar o conteúdo
        with open(local_file_back, "r", encoding="utf-8") as f:
            content = f.read()
            
        print(f"Conteúdo do arquivo retornado: '{content}'")
        if content == "Teste de transferência direta via compartilhamento C$ - MCP":
            print("\n🎉 VALIDAÇÃO DE TRANSFERÊNCIA VIA C$ CONCLUÍDA COM SUCESSO!")
        else:
            print("\n❌ Falha: O conteúdo do arquivo difere.")
            
        # Limpeza
        if os.path.exists(local_file):
            os.remove(local_file)
        if os.path.exists(local_file_back):
            os.remove(local_file_back)
            
        # Apagar o arquivo remoto criado via comando powershell
        print("Limpando arquivo remoto de teste...")
        await server.handle_execute({"command": f"Remove-Item -Path '{remote_file}' -Force -ErrorAction SilentlyContinue"})
        
        # Desconectar
        await server.handle_disconnect()
        
    except Exception as e:
        print(f"❌ Ocorreu um erro durante a validação: {str(e)}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
