"""Extra beat: a seller lists a fix that does not work, and the sandbox catches it before the buyer pays.

    MCP_URL=https://<host>/mcp uv run python demo/broken_fix.py
"""

import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from run_demo import MCP_URL, PACK, PY311_PIP, Agent, shop

# Same listing as Agent A's, but requirements.txt keeps the conflicting pin, so its own install test fails.
BROKEN = {
    **PACK,
    "title": "One-line fix for pip ResolutionImpossible on numpy + scipy 1.16",
    "seller_agent_id": "agent-s",
    "trace": {**PACK["trace"], "solution_files": {**PACK["trace"]["solution_files"], "requirements.txt": "numpy==1.24.*\nscipy==1.16.*\n"}},
}


async def main() -> None:
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as s:
            await s.initialize()
            listed = await Agent(s, "agent-s", PY311_PIP, False).call("publish_pack", BROKEN)
            print(f"agent-s -> publish_pack: {listed['pack_id']} (this fix does not actually work)")
            print(await shop(Agent(s, "agent-e", PY311_PIP, False), listed["pack_id"], follow_recommendation=True))


if __name__ == "__main__":
    asyncio.run(main())
