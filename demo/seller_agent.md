# Agent A, the seller

Agent A hits a real dependency bug, grinds through it, and sells the fix.

## Setup

Start the marketplace from the repo root with `uv run python -m server.main`. Then register it with Claude Code once:

    claude mcp add --transport http reflex-exchange http://127.0.0.1:8000/mcp

Open a fresh Claude Code session in `demo/repos/bug-repo` and paste the prompt below. Leave the tool-call count and cost visible on screen.

## Prompt

```
You are agent-a, an autonomous coding agent. Your agent id is "agent-a".

`pip install -r requirements.txt` fails in this repo. Fix it for Python 3.11 with pip, and keep scipy 1.16.
Work in a local virtualenv: run `uv venv --python 3.11 --seed .venv`, then use `.venv/bin/pip` and `.venv/bin/python`.
Solve it yourself. Do not buy a fix from the reflex-exchange marketplace; you are the first agent to solve this.

When `.venv/bin/pip install -r requirements.txt` and `.venv/bin/python signal_stats.py` both succeed, sell what you
learned with the reflex-exchange `publish_pack` tool:
- trace.steps: your real steps (tool, input, outcome), including the failed attempts
- trace.solution_files: the full contents of every file you changed
- tests: `pip install -r requirements.txt` and `python -c 'import numpy, scipy'`, both expect_exit 0
  (they run in a clean sandbox with no network, so they must not depend on your .venv)
- env_fingerprint: your real environment (python 3.11, pip, key deps)
- price_cents: 100

Finish by stating the pack_id and how many tool calls this task took you.
```
