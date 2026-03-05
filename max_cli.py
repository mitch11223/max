#!/usr/bin/env python3
"""
max_cli.py — CLI entry point for the Max OS agent.

Usage:
    python3 /home/kingmitch/projects/max/max_cli.py "your message"

Returns the full response from Max on stdout.
Called by the OpenClaw Max skill (exec tool).
"""

import asyncio
import json
import sys
from pathlib import Path

# Ensure project root is on path regardless of cwd
_project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(_project_root))


async def main():
    message = " ".join(sys.argv[1:]).strip()
    if not message:
        print("Usage: max_cli.py <message>", file=sys.stderr)
        sys.exit(1)

    import kernel.syscalls as syscalls
    from agents import RootAgent
    from llm import XAIClient, OllamaClient

    # Load xAI API key from the same models.json OpenClaw uses
    models_path = Path.home() / ".openclaw" / "agents" / "main" / "agent" / "models.json"
    xai_key = None
    if models_path.exists():
        with open(models_path) as f:
            data = json.load(f)
        xai_key = data.get("providers", {}).get("xai", {}).get("apiKey")

    grok = XAIClient(api_key=xai_key or "", model="grok-4")
    router = OllamaClient(model="glm-4.7-flash", max_tokens=256, temperature=0.1)

    root = RootAgent(
        config="agents/root.yaml",
        syscall_api=syscalls,
        llm=grok,
        router_llm=router,
    )

    response = await root.chat(message)
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
