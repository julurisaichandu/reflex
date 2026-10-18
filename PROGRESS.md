# Progress

| Phase | Status | Notes |
|---|---|---|
| 0 Skeleton loop | done | `uv run python demo/run_demo.py` against `uv run python -m server.main` |
| 1 Real sandbox | todo | fixtures built and proven offline at 23:20 |
| 2 Real Stripe | todo | needs `STRIPE_SECRET_KEY` |
| 3 Warnings + compatibility | todo | |
| 4 Demo assets | todo | |
| 5 Deploy + polish | todo | needs Manufact account and your go to push |
| 6 Stretch | todo | |

## Blockers

- Supabase `DATABASE_URL` (session pooler). Running on local Postgres until then.
- Stripe test key.

## Log

- 23:00 Repo created. Docker Desktop started.
- 23:12 `supabase_schema.sql` view fixed. `group by 1, 2, 3, 4, 5` included the `passes` aggregate and Postgres rejected it.
- 23:20 Fixture images built. Buggy pin gives ResolutionImpossible offline, relaxed pin installs numpy 1.26.4 + scipy 1.16.3, py312-pnpm has no pip (exit 127).
- 23:40 Phase 0 checkpoint passed. The four tools run end to end over MCP HTTP with stub payment and sandbox.
- Known mcp-use 1.7.1 bug: a tools/call before any tools/list crashed in its middleware. `server/main.py` warms the SDK tool cache at startup.
