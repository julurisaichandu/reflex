"""Non-interactive A -> B -> C -> D demo against a running Reflex Exchange MCP server.

    uv run python demo/run_demo.py --reset             # local server, empty marketplace first
    uv run python demo/run_demo.py --reset-only        # empty the marketplace before live agent sessions
    uv run python demo/run_demo.py --json              # also print every raw response
    uv run python demo/run_demo.py --pace 4            # pause between beats for narration
    MCP_URL=https://<host>/mcp uv run python demo/run_demo.py
"""

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_URL = os.environ.get("MCP_URL", "http://127.0.0.1:8000/mcp")
GREEN, RED, YELLOW, BOLD, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[1m", "\033[2m", "\033[0m"

PY311_PIP = {"language": "python", "language_version": "3.11", "os": "linux", "package_manager": "pip", "key_deps": ["numpy", "scipy"]}
PY312_PNPM = {"language": "python", "language_version": "3.12", "os": "linux", "package_manager": "pnpm", "key_deps": ["numpy", "scipy"]}
TASK = "pip install failing with ResolutionImpossible on numpy"

# Agent A's fix for demo/repos/bug-repo, as the scripted seller publishes it.
PROOFPACK = Path(__file__).resolve().parent / "proofpack"

PACK = {
    "title": "Upgrade to scipy 1.16: fix pip ResolutionImpossible and the numpy/scipy APIs it removed",
    "task_signature": "pip install fails: ResolutionImpossible numpy scipy 1.16; then AttributeError simps binom_test, interp2d removed",
    "description": (
        "scipy 1.16 needs numpy>=1.25.2, so a numpy==1.24.* pin cannot resolve. Once it does, scipy 1.16 has removed "
        "integrate.simps, stats.binom_test and interp2d: port them to simpson(x=), binomtest().pvalue and "
        "RectBivariateSpline(kx=1, ky=1), and replace the numpy aliases removed in 2.0."
    ),
    "trace": {
        "steps": [
            {"tool": "bash", "input": "pip install -r requirements.txt", "outcome": "error"},
            {"tool": "edit", "input": "requirements.txt: numpy==1.24.* -> numpy>=1.25.2,<2", "outcome": "ok"},
            {"tool": "bash", "input": "python -m unittest discover -s tests", "outcome": "error"},
            {"tool": "edit", "input": "stats.py: simps(y, t) -> simpson(y, x=t); binom_test(...) -> binomtest(...).pvalue", "outcome": "ok"},
            {"tool": "edit", "input": "stats.py: interp2d(x, y, z)(xs, ys) -> RectBivariateSpline(y, x, z, kx=1, ky=1)(ys, xs)", "outcome": "ok"},
            {"tool": "edit", "input": "stats.py: np.float_ -> np.float64, np.NaN -> np.nan, np.product -> np.prod", "outcome": "ok"},
            {"tool": "bash", "input": "python -m unittest discover -s tests", "outcome": "ok"},
        ],
        "solution_files": {
            str(p.relative_to(PROOFPACK)): p.read_text()
            for p in sorted(PROOFPACK.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts
        },
    },
    "tests": [
        {"cmd": "pip install -r requirements.txt", "expect_exit": 0},
        {"cmd": "python -m unittest discover -s tests", "expect_exit": 0},
    ],
    "env_fingerprint": PY311_PIP,
    "price_cents": 100,
    "seller_agent_id": "agent-a",
}


class Agent:
    def __init__(self, session: ClientSession, agent_id: str, fp: dict, raw: bool):
        self.s, self.id, self.fp, self.raw = session, agent_id, fp, raw
        self.calls = 0

    async def call(self, tool: str, args: dict) -> dict:
        self.calls += 1
        res = await self.s.call_tool(tool, args)
        data = json.loads(res.content[0].text)
        if self.raw:
            print(f"{DIM}{tool} -> {json.dumps(data, indent=2)}{RESET}")
        return data


def money(cents: int) -> str:
    return f"${cents / 100:.2f}"


def beat(title: str, pace: float) -> None:
    time.sleep(pace)
    print(f"\n{BOLD}{'=' * 78}\n{title}\n{'=' * 78}{RESET}")


def show_discover(d: dict) -> dict | None:
    for p in d["packs"]:
        rec = p["recommendation"]
        color = {"recommended": GREEN, "not_recommended": RED}.get(rec, YELLOW)
        compat = ", ".join(f"{c['fingerprint_summary']} {c['status']} x{c['observations']}" for c in p["compatibility"]) or "no verifications yet"
        print(f"  {p['pack_id']}  {p['title']}  {money(p['price_cents'])}")
        print(f"    compatibility: {compat}")
        print(f"    recommendation for your env: {color}{BOLD}{rec}{RESET}")
        for w in p["warnings_for_your_env"]:
            print(f"    {RED}warning {w['warning_id']}: {w['summary']}{RESET}")
    return d["packs"][0] if d["packs"] else None


async def shop(agent: Agent, pack_id: str, follow_recommendation: bool) -> dict:
    print(f"{agent.id} -> discover_packs({TASK!r})")
    listing = show_discover(await agent.call("discover_packs", {"task_description": TASK, "env_fingerprint": agent.fp}))
    if listing and listing["recommendation"] == "not_recommended" and follow_recommendation:
        print(f"{agent.id} follows the recommendation and does not buy. {GREEN}Spent $0.00.{RESET}")
        print(f"{agent.id} -> acquire_pack anyway, to show the marketplace guard")
    else:
        print(f"{agent.id} -> acquire_pack({pack_id})")
    tx = await agent.call("acquire_pack", {"pack_id": pack_id, "buyer_agent_id": agent.id, "env_fingerprint": agent.fp})
    if "error" in tx:
        code = tx["error"]["code"]
        print(f"  {RED}refused: {code}{RESET}. No payment was created.")
        return {"outcome": "warned before paying" if code == "warning_exists" else code, "paid": "$0.00", "pi": "none created"}
    print(f"  hold placed: {money(tx['amount_cents'])} {tx['payment_status']}, {tx['transaction_id']}, Stripe {tx['stripe_payment_intent_id']}")
    print(f"{agent.id} -> verify_and_settle({tx['transaction_id']})  (marketplace sandbox: no network, 1 CPU, 512 MB, non-root)")
    v = await agent.call("verify_and_settle", {"transaction_id": tx["transaction_id"]})
    if "error" in v:
        print(f"  {RED}{v['error']['code']}: {v['error']['message']}{RESET}")
        return {"outcome": v["error"]["code"], "paid": "$0.00", "pi": tx["stripe_payment_intent_id"]}
    if v["result"] == "pass":
        files = ", ".join(v["pack"]["solution_files"])
        print(f"  {GREEN}{BOLD}PASS{RESET}{GREEN}: {v['pack']['tests_passed']} tests passed -> payment CAPTURED -> delivered {files}{RESET}")
        requirements = v["pack"]["solution_files"].get("requirements.txt", "")
        print(f"{DIM}    --- requirements.txt\n" + "".join(f"    {line}\n" for line in requirements.splitlines()) + RESET, end="")
        return {"outcome": "verified, pack delivered", "paid": money(v["receipt"]["amount_cents"]), "pi": tx["stripe_payment_intent_id"]}
    e = v["evidence"]
    print(f"  {RED}{BOLD}FAIL{RESET}{RED} in fixture {e['fixture']}: `{e['failed_test']}` exited {e['exit_code']} ({e['error_class']})")
    print(f"  -> authorization CANCELED, not charged -> warning {v['warning_id']} published{RESET}")
    return {"outcome": "verification failed, hold released", "paid": "$0.00", "pi": tx["stripe_payment_intent_id"]}


def reset() -> None:
    import psycopg

    load_dotenv()
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute("truncate warnings, verifications, transactions, packs")
    print(f"{DIM}marketplace reset: packs, transactions, verifications, warnings truncated{RESET}")


async def main(args: argparse.Namespace) -> None:
    if args.reset or args.reset_only:
        reset()
    if args.reset_only:
        return
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as s:
            await s.initialize()
            seller = Agent(s, "agent-a", PY311_PIP, args.json)
            b, c, d = (Agent(s, "agent-b", PY311_PIP, args.json), Agent(s, "agent-c", PY312_PNPM, args.json),
                       Agent(s, "agent-d", PY312_PNPM, args.json))

            if args.pack_id:
                listed = {"pack_id": args.pack_id}
                print(f"Using live seller's pack {args.pack_id}")
            else:
                beat("A  Seller agent publishes the fix it worked out as a ProofPack", 0)
                listed = await seller.call("publish_pack", PACK)
                print(f"agent-a -> publish_pack: {listed['pack_id']} {listed['status']} at {money(PACK['price_cents'])}, "
                      f"{len(PACK['tests'])} tests, fingerprint python3.11/pip")

            beat("B  Buyer on python3.11/pip pays only after the sandbox proves the fix", args.pace)
            rb = await shop(b, listed["pack_id"], follow_recommendation=True)
            beat("C  Buyer on python3.12/pnpm: verification fails, hold canceled, failure published", args.pace)
            rc = await shop(c, listed["pack_id"], follow_recommendation=True)
            beat("D  Next python3.12/pnpm buyer is warned before spending anything", args.pace)
            rd = await shop(d, listed["pack_id"], follow_recommendation=True)

            beat("Ledger", args.pace)
            print(f"{'agent':9}{'environment':18}{'calls':7}{'paid':8}{'stripe':30}outcome")
            for agent, r in ((b, rb), (c, rc), (d, rd)):
                env = f"{agent.fp['language']}{agent.fp['language_version']}/{agent.fp['package_manager']}"
                print(f"{agent.id:9}{env:18}{agent.calls:<7}{r['paid']:8}{r['pi']:30}{r['outcome']}")
            print(f"\n{BOLD}The marketplace sells successes and gives away failures.{RESET}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="truncate marketplace tables first (uses DATABASE_URL)")
    parser.add_argument("--reset-only", action="store_true", help="truncate marketplace tables and exit")
    parser.add_argument("--pack-id", help="skip beat A and run B, C, D against a pack a live seller already published")
    parser.add_argument("--json", action="store_true", help="print every raw tool response")
    parser.add_argument("--pace", type=float, default=0, help="seconds to pause before each beat")
    asyncio.run(main(parser.parse_args()))
