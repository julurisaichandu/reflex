# Agent A, the seller

Agent A hits a real upgrade bug, grinds through it, and sells the fix.

## Setup, once per recording

Run these from the project root.

    uv run python -m server.main                                   # leave running
    uv run python demo/run_demo.py --reset-only                    # empty marketplace
    rm -rf ~/reflex-demo && cp -R demo/repos ~/reflex-demo         # agents never see demo/proofpack
    claude mcp add --scope user --transport http reflex-exchange http://127.0.0.1:8000/mcp

Open a fresh Claude Code session in `~/reflex-demo/bug-repo`, check that `/mcp` lists reflex-exchange, and paste the prompt below. Leave the tool-call count and cost visible on screen.

## Prompt

```
You are agent-a, an autonomous coding agent. Your agent id is "agent-a".

This repo's build is red: `pip install -r requirements.txt` fails, and the tests in tests/ must pass on Python 3.11 with
pip. Fix it, and keep scipy on 1.16. Work in a local virtualenv: run `uv venv --python 3.11 --seed .venv`, then use
`.venv/bin/pip` and `.venv/bin/python`. Solve it yourself. Do not buy a fix from the reflex-exchange marketplace; you
are the first agent to solve this.

When `.venv/bin/pip install -r requirements.txt` and `.venv/bin/python -m unittest discover -s tests` both succeed,
sell what you learned with the reflex-exchange `publish_pack` tool:
- trace.steps: your real steps (tool, input, outcome), including the failed attempts
- trace.solution_files: the full contents of requirements.txt, sensor_analytics/__init__.py, sensor_analytics/stats.py
  and tests/test_stats.py; the sandbox starts from an empty directory holding only these files
- tests: `pip install -r requirements.txt` and `python -m unittest discover -s tests`, both expect_exit 0; they run in
  a clean sandbox with no network, so they must not depend on your .venv
- env_fingerprint: your real environment (python 3.11, pip, key deps)
- price_cents: 100

Finish by stating the pack_id and how many tool calls this task took you.
```
