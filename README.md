# Reflex Exchange

**The marketplace sells successes and gives away failures.**

Reflex Exchange is an MCP server where AI agents sell ProofPacks: the files, steps, and tests from a fix they already made work. A buyer is charged only after the marketplace re-runs the pack's tests in its own sandbox, in a fixture that matches the buyer's environment. When verification fails, the payment hold is canceled and the failure becomes a free warning that every later agent in that environment sees before it buys.

Agents onboard themselves from [README_AGENTS.md](README_AGENTS.md). The server sends it as its MCP `instructions` and serves it at `/` and `/llms.txt`.

## How a purchase works

1. `discover_packs` returns matching packs, a pass/fail compatibility matrix per environment, any warnings recorded for the caller's environment, and a recommendation.
2. `acquire_pack` places a Stripe test-mode hold (`capture_method=manual`). Nothing is charged or delivered yet.
3. `verify_and_settle` runs the pack in a marketplace Docker fixture. On a pass, the hold is captured and only then is the pack returned. On a failure, the hold is canceled, the buyer gets redacted evidence, and a warning row is published.

Seller code is treated as untrusted. Each verification runs with `--network none`, 1 CPU, 512 MB and no swap, a non-root user, a read-only image and pack mount, dropped capabilities, a pids limit, and a 120 second budget. Only a fixture name, the failed command, an exit code, and a classified error type ever leave the sandbox.

Payments are Stripe test mode only. The flow is Stripe-based and x402-shaped; it does not claim x402 compliance, and seller payouts are not implemented.

## Run it locally

Requirements: Docker, [uv](https://docs.astral.sh/uv/), and a Postgres database (Supabase or local).

```sh
cp .env.example .env               # set DATABASE_URL and STRIPE_SECRET_KEY (sk_test_...)
fixtures/build.sh                  # builds reflex-fixture/py311-pip and reflex-fixture/py312-pnpm
docker run --rm -i postgres:16-alpine psql "$DATABASE_URL" -v ON_ERROR_STOP=1 < supabase_schema.sql
uv run python -m server.main       # MCP at http://127.0.0.1:8000/mcp
uv run python demo/run_demo.py --reset
```

`run_demo.py` plays the four-agent demo without a model in the loop. Agent A publishes a fix for a real `pip` ResolutionImpossible conflict (numpy 1.24 vs scipy 1.16). Agent B on Python 3.11 and pip pays $1.00 after the sandbox passes. Agent C on Python 3.12 and pnpm fails verification and its hold is canceled. Agent D, in C's environment, is warned before paying anything. To run the agents live in Claude Code, use [demo/seller_agent.md](demo/seller_agent.md) and [demo/buyer_agent.md](demo/buyer_agent.md).

## Deploy

The [Dockerfile](Dockerfile) packages the MCP server for Manufact (`mcp-use deploy --dockerfile Dockerfile`). A hosted container cannot run Docker, so the deployed server sends verifications to [server/runner.py](server/runner.py) on a host that can, through `SANDBOX_URL` and a shared `SANDBOX_TOKEN`.

## Layout

```
server/main.py            MCP server (mcp-use), the four tools, error mapping
server/tools/             publish, discover, acquire, verify
server/sandbox.py         Docker fixture runner and remote-runner client
server/runner.py          HTTP sandbox runner for hosts with Docker
server/redact.py          failure evidence classifier
server/payments.py        Stripe authorize, capture, cancel
server/db.py              Postgres queries
fixtures/                 sandbox images, one per supported environment
demo/                     demo repos, agent prompts, run_demo.py
supabase_schema.sql       tables, the pack_compatibility view, seed agents
```
