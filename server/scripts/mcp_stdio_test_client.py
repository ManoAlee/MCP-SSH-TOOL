#!/usr/bin/env python3
import asyncio
import os
import sys
from pathlib import Path

import mcp
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession


async def main():
    repo_root = Path(__file__).resolve().parents[1]
    # Ensure uvx is found: prefix PATH with user .local\bin
    user_bin = str(Path.home() / ".local" / "bin")
    env = os.environ.copy()
    env["PATH"] = user_bin + os.pathsep + env.get("PATH", "")

    server_params = StdioServerParameters(
        command="uvx",
        args=["run", "ssh-connect"],
        cwd=str(repo_root),
        env=env,
    )

    print("Starting stdio client and spawning server via uvx...")

    async with stdio_client(server_params) as (read, write):
        session = ClientSession(read, write)
        print("Initializing client session...")
        init = await session.initialize()
        print("Server initialize result:", init)

        print("Listing tools...")
        tools = await session.list_tools()
        print("Tools:")
        for t in tools.tools:
            print(" -", t.name)

        # Try calling list_files (expected to error if not connected)
        try:
            print("Calling tools/call -> list_files (should error if not connected)")
            res = await session.call_tool("list_files", {"path": "."})
            print("call_tool result:", res)
        except Exception as e:
            print("call_tool raised:", e)

        # Try ping
        try:
            await session.send_ping()
            print("Ping OK")
        except Exception as e:
            print("Ping failed:", e)


if __name__ == "__main__":
    asyncio.run(main())
