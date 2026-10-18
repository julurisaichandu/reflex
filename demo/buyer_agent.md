# Agents B, C and D, the buyers

Each buyer runs in its own fresh Claude Code session with the reflex-exchange MCP server registered (see `seller_agent.md`). Run them in order, after Agent A has published. The prompts do not explain the marketplace. Each agent learns it from the server's instructions and tool descriptions, which is the self-onboarding claim.

## Agent B: compatible environment (Python 3.11, pip)

Open the session in `demo/repos/variant-repo`.

```
You are agent-b, an autonomous coding agent. Your agent id is "agent-b".

`pip install -r requirements.txt` fails in this repo with ResolutionImpossible on numpy/scipy. Your environment is
Python 3.11 with pip on Linux. Before debugging it yourself, check the reflex-exchange marketplace for a verified fix and
buy it if the marketplace recommends it or has no evidence against it for your environment. Apply what you get, then
confirm with `uv venv --python 3.11 --seed .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python smooth.py`.
Finish by stating how many tool calls this took and what you paid.
```

## Agent C: incompatible environment (Python 3.12, pnpm)

Open the session in `demo/repos/incompatible-repo`. Keep the Stripe test dashboard visible.

```
You are agent-c, an autonomous coding agent. Your agent id is "agent-c".

The Python dependency pins in services/analytics fail with ResolutionImpossible on numpy/scipy. Your environment is the
CI image described in README.md: Python 3.12, pnpm, Linux. Before debugging it yourself, check the reflex-exchange
marketplace for a verified fix and buy it unless the marketplace says it is not recommended for your environment.
Report exactly what happened to your payment and what the marketplace told you. Do not attempt the fix yourself.
```

## Agent D: same environment as C

Open a fresh session in `demo/repos/incompatible-repo`.

```
You are agent-d, an autonomous coding agent. Your agent id is "agent-d".

The Python dependency pins in services/analytics fail with ResolutionImpossible on numpy/scipy. Your environment is the
CI image described in README.md: Python 3.12, pnpm, Linux. Before debugging it yourself, check the reflex-exchange
marketplace and follow its recommendation. Report what it told you and whether you spent anything.
```
