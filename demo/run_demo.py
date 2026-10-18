"""Non-interactive demo flow against a running Reflex Exchange MCP server.

    uv run python demo/run_demo.py            # server at http://127.0.0.1:8000/mcp
    MCP_URL=https://.../mcp uv run python demo/run_demo.py
"""

import asyncio
import json
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_URL = os.environ.get("MCP_URL", "http://127.0.0.1:8000/mcp")

PY311_PIP = {"language": "python", "language_version": "3.11", "os": "linux", "package_manager": "pip", "key_deps": ["numpy", "scipy"]}
PY312_PNPM = {"language": "python", "language_version": "3.12", "os": "linux", "package_manager": "pnpm", "key_deps": ["numpy"]}
TASK = "pip install failing with ResolutionImpossible on numpy"

PACK = {
    "title": "Fix pip ResolutionImpossible on pinned numpy/scipy conflict",
    "task_signature": "pip install fails: ResolutionImpossible numpy scipy",
    "description": "scipy 1.16 needs numpy>=1.25.2, so a numpy==1.24.* pin cannot resolve. Relax the numpy pin to >=1.24,<2 and reinstall.",
    "trace": {
        "steps": [
            {"tool": "bash", "input": "pip install -r requirements.txt", "outcome": "error"},
            {"tool": "edit", "input": "requirements.txt: numpy==1.24.* -> numpy>=1.24,<2", "outcome": "ok"},
            {"tool": "bash", "input": "pip install -r requirements.txt", "outcome": "ok"},
        ],
        "solution_files": {"requirements.txt": "numpy>=1.24,<2\nscipy==1.16.*\n"},
    },
    "tests": [
        {"cmd": "pip install -r requirements.txt", "expect_exit": 0},
        {"cmd": "python -c 'import numpy, scipy'", "expect_exit": 0},
    ],
    "env_fingerprint": PY311_PIP,
    "price_cents": 100,
    "seller_agent_id": "agent-a",
}


async def call(session: ClientSession, tool: str, args: dict) -> dict:
    res = await session.call_tool(tool, args)
    data = json.loads(res.content[0].text)
    print(f"\n>>> {tool} {json.dumps(args)}\n{json.dumps(data, indent=2)}")
    return data


def beat(title: str) -> None:
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


async def buy(s: ClientSession, agent: str, fp: dict, pack_id: str) -> dict:
    await call(s, "discover_packs", {"task_description": TASK, "env_fingerprint": fp})
    tx = await call(s, "acquire_pack", {"pack_id": pack_id, "buyer_agent_id": agent, "env_fingerprint": fp})
    if "error" in tx:
        return tx
    return await call(s, "verify_and_settle", {"transaction_id": tx["transaction_id"]})


async def main() -> None:
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as s:
            await s.initialize()
            beat("A  Seller agent publishes its fix as a ProofPack")
            pack_id = (await call(s, "publish_pack", PACK))["pack_id"]
            beat("B  Buyer on python3.11/pip: verify passes, payment captured, pack delivered")
            await buy(s, "agent-b", PY311_PIP, pack_id)
            beat("C  Buyer on python3.12/pnpm: verify fails, authorization canceled, warning published")
            await buy(s, "agent-c", PY312_PNPM, pack_id)
            beat("D  Another python3.12/pnpm buyer is warned before paying anything")
            await buy(s, "agent-d", PY312_PNPM, pack_id)


if __name__ == "__main__":
    asyncio.run(main())
