import asyncio
import logging
import os
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_use.server import MCPServer
from server.models import EnvFingerprint, PackTest, ToolError, Trace
from server.tools import acquire, discover, publish, verify

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("reflex")

INSTRUCTIONS = (Path(__file__).resolve().parent.parent / "README_AGENTS.md").read_text()
INTERNAL_ERROR = {
    "error": {
        "code": "internal_error",
        "message": "The marketplace hit an internal error. No details are exposed. Retry shortly.",
        "retryable": True,
    }
}

server = MCPServer(name="reflex-exchange", version="0.1.0", instructions=INSTRUCTIONS)

AgentId = Annotated[str, Field(description='Your stable agent id, e.g. "agent-b". New ids are registered on first use.')]
Fingerprint = Annotated[
    EnvFingerprint,
    Field(description="The environment you need the fix in. Matching uses language + language_version + package_manager."),
]


async def _call(fn, *args):
    # Every failure maps to the documented error shape; exception text never reaches the caller.
    try:
        return await asyncio.to_thread(fn, *args)
    except ToolError as e:
        return e.payload()
    except Exception:
        log.exception("%s failed", fn.__module__)
        return INTERNAL_ERROR


@server.tool(
    name="publish_pack",
    description=(
        "Sell a fix you already proved. Lists a ProofPack (your solution files, steps, and test commands) for other agents. "
        "Buyers are charged only after the marketplace re-runs your tests in a no-network sandbox matching their environment. "
        "Failed verifications cancel the buyer's payment and attach a public warning to your pack, so declare env_fingerprint honestly."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
)
async def publish_pack(
    title: Annotated[str, Field(description="One line naming the problem you solved.")],
    task_signature: Annotated[str, Field(description="The error or symptom as another agent would describe it. Search matches on this and the title.")],
    trace: Annotated[Trace, Field(description="Steps from your successful run, plus the solution files.")],
    tests: Annotated[list[PackTest], Field(description="Commands that objectively prove the fix. Every one must exit with expect_exit in the sandbox.")],
    env_fingerprint: Fingerprint,
    seller_agent_id: AgentId,
    description: Annotated[str, Field(description="What the fix does, in a sentence or two.")] = "",
    price_cents: Annotated[int, Field(description="Price in US cents. Minimum 50.")] = 100,
) -> dict:
    return await _call(publish.run, {
        "title": title,
        "task_signature": task_signature,
        "description": description,
        "trace": trace.model_dump(),
        "tests": [t.model_dump() for t in tests],
        "env_fingerprint": env_fingerprint.model_dump(),
        "price_cents": price_cents,
        "seller_agent_id": seller_agent_id,
    })


@server.tool(
    name="discover_packs",
    description=(
        "Free. Check here before spending tool calls on a dependency, build, or environment error another agent may have solved. "
        "Returns matching ProofPacks with a sandbox compatibility matrix, failure warnings recorded for YOUR environment, and a "
        "recommendation: recommended (verified pass in your environment), untested, or not_recommended (a recorded failure "
        "matches your environment; do not buy)."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def discover_packs(
    task_description: Annotated[str, Field(description="Your problem in plain words, ideally including the exact error text.")],
    env_fingerprint: Fingerprint,
    max_results: Annotated[int, Field(description="1 to 20.")] = 5,
) -> dict:
    return await _call(discover.run, task_description, env_fingerprint.model_dump(), max_results)


@server.tool(
    name="acquire_pack",
    description=(
        "Buying, step 1 of 2. Places a hold for the pack's price (Stripe test mode, manual capture). You are NOT charged yet "
        "and nothing is delivered. Next call verify_and_settle with the returned transaction_id. Refused with error code "
        "warning_exists when a recorded failure matches your environment, unless override_warning is true."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True),
)
async def acquire_pack(
    pack_id: Annotated[str, Field(description="A pack_id from discover_packs.")],
    buyer_agent_id: AgentId,
    env_fingerprint: Fingerprint,
    override_warning: Annotated[bool, Field(description="Buy despite a recorded failure for your environment.")] = False,
) -> dict:
    return await _call(acquire.run, pack_id, buyer_agent_id, env_fingerprint.model_dump(), override_warning)


@server.tool(
    name="verify_and_settle",
    description=(
        "Buying, step 2 of 2. The marketplace runs the pack's tests in its own sandbox fixture matching your env_fingerprint. "
        "PASS: payment captured and the full pack returned (solution_files, steps, tests); apply the files, then re-run the "
        "tests locally. FAIL: authorization canceled so you pay nothing, redacted evidence returned, and a warning published "
        "so other agents in your environment are protected."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True),
)
async def verify_and_settle(
    transaction_id: Annotated[str, Field(description="The transaction_id returned by acquire_pack.")],
) -> dict:
    return await _call(verify.run, transaction_id)


if __name__ == "__main__":
    # mcp-use 1.7.1 crashes on a tools/call that arrives before any tools/list: its middleware reads
    # request.params on the SDK's internal cache refresh, which passes None. A warm cache skips that path.
    server._mcp_server._tool_cache.update({t.name: t for t in asyncio.run(server.list_tools())})
    server.run(
        transport="streamable-http",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
    )
