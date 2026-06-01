import asyncio
import subprocess
import socket
import sys
import os
import base64

def get_ad_computers():
    print("Obtendo lista de computadores do Active Directory...")
    try:
        cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", "Get-ADComputer -Filter * | Select-Object -ExpandProperty Name"]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        computers = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        print(f"Total de computadores encontrados no AD: {len(computers)}")
        return computers
    except Exception as e:
        print(f"Erro ao consultar Active Directory: {e}")
        # Retorna lista vazia ou lista local mock se necessário
        return []

async def check_port_5985(computer, timeout=2.0):
    try:
        # Tenta abrir conexão TCP na porta do WinRM (5985)
        fut = asyncio.open_connection(computer, 5985)
        reader, writer = await asyncio.wait_for(fut, timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except:
            pass
        return True
    except Exception:
        return False

async def test_winrm_auth(computer, timeout=10):
    cmd_str = f"Invoke-Command -ComputerName '{computer}' -ScriptBlock {{ hostname }}"
    full_cmd = f"$ProgressPreference = 'SilentlyContinue'; {cmd_str}"
    encoded_cmd = base64.b64encode(full_cmd.encode('utf-16-le')).decode('utf-8')
    
    proc = await asyncio.create_subprocess_exec(
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-EncodedCommand",
        encoded_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode == 0:
            return True, stdout_bytes.decode('utf-8', errors='replace').strip()
        else:
            err = stderr_bytes.decode('utf-8', errors='replace').strip()
            # Limpar erros clixml/verbose chatos se houver
            if err.startswith("#< CLIXML"):
                err = "Falha na autenticação/permissão de acesso WinRM"
            return False, err.replace("\r", " ").replace("\n", " ")[:100]
    except Exception as e:
        try:
            proc.kill()
        except:
            pass
        return False, str(e)

async def scan_computer(computer):
    # Passo 1: Ping/Port scan rápido
    port_open = await check_port_5985(computer)
    if not port_open:
        return {
            "computer": computer,
            "port_5985": "Fechada/Offline",
            "auth_ok": False,
            "details": "Offline ou WinRM desativado"
        }
    
    # Passo 2: Testar autenticação remota
    auth_ok, details = await test_winrm_auth(computer)
    return {
        "computer": computer,
        "port_5985": "Aberta",
        "auth_ok": auth_ok,
        "details": "Conectado com sucesso!" if auth_ok else f"Falha de Autenticação: {details}"
    }

async def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
    computers = get_ad_computers()
    if not computers:
        print("Nenhum computador encontrado.")
        return

    print("Iniciando varredura paralela de conectividade WinRM (Porta 5985)...")
    tasks = [scan_computer(c) for c in computers]
    results = await asyncio.gather(*tasks)

    # Ordenar por status (Conectados primeiro, depois porta aberta com falha, depois offline)
    def sort_key(r):
        if r["auth_ok"]:
            return 0
        elif r["port_5985"] == "Aberta":
            return 1
        else:
            return 2

    results.sort(key=sort_key)

    # Imprimir tabela markdown
    print("\n### Relatório de Conectividade do Domínio (MCP / PowerShell Remoting)\n")
    print("| Computador | Porta 5985 (WinRM) | Conexão MCP | Detalhes / Status |")
    print("| :--- | :--- | :--- | :--- |")
    for r in results:
        status_mcp = "🟢 Sucesso" if r["auth_ok"] else ("🟡 Porta Aberta (Sem Acesso)" if r["port_5985"] == "Aberta" else "🔴 Inacessível")
        print(f"| {r['computer']} | {r['port_5985']} | {status_mcp} | {r['details']} |")

if __name__ == "__main__":
    # Ajuste para evitar warnings no loop assíncrono do Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
