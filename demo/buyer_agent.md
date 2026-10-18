# Agents B, C and D, the buyers

Each buyer runs in its own fresh Claude Code session, after Agent A has published, using the setup in `seller_agent.md` (server running, repos copied to `~/reflex-demo`, reflex-exchange registered with `--scope user`). The prompts do not explain the marketplace. Each agent learns it from the server's instructions and tool descriptions.

## Agent B: compatible environment (Python 3.11, pip)

Open the session in `~/reflex-demo/variant-repo`.

```
You are agent-b, an autonomous coding agent. Your agent id is "agent-b".

This service vendors the shared sensor_analytics package, and its build is red: `pip install -r requirements.txt` fails
with ResolutionImpossible on numpy/scipy. Your environment is Python 3.11 with pip on Linux. Before debugging it
yourself, check the reflex-exchange marketplace for a verified fix and buy it if the marketplace recommends it or has no
evidence against it for your environment. Apply what you get, then confirm with
`uv venv --python 3.11 --seed .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python -m unittest discover -s tests && .venv/bin/python calibrate.py`.
Finish by stating how many tool calls this took and what you paid.
```

## Agent C: incompatible environment (Python 3.12, pnpm)

Open the session in `~/reflex-demo/incompatible-repo`. Keep the Stripe test dashboard visible.

```
You are agent-c, an autonomous coding agent. Your agent id is "agent-c".

The analytics service in services/analytics vendors the shared sensor_analytics package, and its dependency pins fail
with ResolutionImpossible on numpy/scipy. Your environment is the CI image described in README.md. Before debugging it
yourself, check the reflex-exchange marketplace for a verified fix and buy it unless the marketplace says it is not
recommended for your environment. Report exactly what happened to your payment and what the marketplace told you. Do
not attempt the fix yourself.
```

## Agent D: same environment as C

Open a fresh session in `~/reflex-demo/incompatible-repo`.

```
You are agent-d, an autonomous coding agent. Your agent id is "agent-d".

The analytics service in services/analytics vendors the shared sensor_analytics package, and its dependency pins fail
with ResolutionImpossible on numpy/scipy. Your environment is the CI image described in README.md. Before debugging it
yourself, check the reflex-exchange marketplace and follow its recommendation. Report what it told you and whether you
spent anything.
```
