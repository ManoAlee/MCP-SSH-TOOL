#!/usr/bin/env python3
import asyncio
import os
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PATH"] = str(Path.home() / ".local" / "bin") + os.pathsep + env.get("PATH", "")
    env["SSH_MCP_LOG"] = r"C:\ssh-mcp\ssh-mcp.log"
    command = os.environ.get("MCP_COMMAND", "uvx")
    args = os.environ.get("MCP_ARGS", "run ssh-connect").split()
    server = StdioServerParameters(
        command=command,
        args=args,
        cwd=str(repo_root),
        env=env,
    )

    print(f"starting stdio_client with command={command!r} args={args!r}")
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            print("initializing")
            result = await asyncio.wait_for(session.initialize(), timeout=20)
            print("initialized:", result.protocolVersion)

            print("listing tools")
            tools = await asyncio.wait_for(session.list_tools(), timeout=20)
            print("tool-count:", len(tools.tools))
            print("tool-names:", [tool.name for tool in tools.tools])


if __name__ == "__main__":
    asyncio.run(main())
