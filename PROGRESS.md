# Progress

| Phase | Status | Notes |
|---|---|---|
| 0 Skeleton loop | done | `uv run python demo/run_demo.py` against `uv run python -m server.main` |
| 1 Real sandbox | done | `fixtures/build.sh`, then `uv run python demo/run_demo.py` |
| 2 Real Stripe | done | captured and canceled PaymentIntents match transaction rows |
| 3 Warnings + compatibility | done on stub payments | override, no_fixture, re-verify, traversal, and empty-tests paths checked |
| 4 Demo assets | done | `uv run python demo/run_demo.py --reset` runs A to D on real Stripe and the real sandbox in 6 s |
| 5 Deploy + polish | done | https://warm-wave-zjjim.run.mcp-use.com/mcp on Manufact, Supabase, sandbox runner behind cloudflared; full demo verified through it; dashboard and `/present` slides in `demo/` |
| 6 Stretch | decided: skip custos and Deja Do | custos badge would rest on a seller-supplied log; Deja Do cannot see heredoc edits and extracts after publish |

## Blockers

- None. The sandbox runner lives on the demo laptop behind a cloudflared quick tunnel, so verification needs that laptop online; a restarted tunnel gets a new URL and needs `SANDBOX_URL` updated on Manufact.

## Log

- 23:00 Repo created. Docker Desktop started.
- 23:05 `supabase_schema.sql` view fixed. `group by 1, 2, 3, 4, 5` included the `passes` aggregate and Postgres rejected it.
- 23:08 Fixture images built. Buggy pin gives ResolutionImpossible offline, relaxed pin installs numpy 1.26.4 + scipy 1.16.3, py312-pnpm has no pip (exit 127).
- 23:14 Phase 0 checkpoint passed. The four tools run end to end over MCP HTTP with stub payment and sandbox.
- Known mcp-use 1.7.1 bug: a tools/call before any tools/list crashed in its middleware. `server/main.py` warms the SDK tool cache at startup.
- 23:17 Phase 1 checkpoint passed. Same pack passes on py311-pip (2.6 s) and fails on py312-pnpm (exit 127, CommandNotFound), redacted evidence stored. Hostile tests contained: network, rootfs and pack writes, env secrets, 50 MB output, 900 MB allocation, fork bomb, 60 s sleep.
- 23:20 Phase 3 paths verified. Phase 4 assets written. The bug and fix reproduce on the laptop against real PyPI.
- 23:21 Background review workflow running (money, leaks, sandbox, spec, agent usability).
- 23:27 Phase 2 checkpoint passed. API 2026-09-30 rejects `payment_method_types`; switched to `allowed_payment_method_types`. agent-b PI succeeded ($1.00 received), agent-c PI canceled ($0), both match DB rows.
- 23:27 Phase 4 checkpoint passed with real Stripe and the real sandbox.
- 23:29 Deploy image proven: MCP server container (uid 10001, no Docker) plus host sandbox runner plus real Stripe ran all four beats. README_AGENTS.md updated for drift.
- 23:31 Armature dry run started: fresh headless Claude Code session given only the local server URL.
- 23:36 First Armature dry run: a fresh agent never called the marketplace and fixed the one-line pin bug itself (4 calls, $0.13). Demo bug replaced by a scipy 1.16 upgrade.
- 23:40 Second dry run: the agent called discover_packs on its own, but the free description held the fix. Listings now carry only symptom and environment.
- 23:43 Measured the demo bug without the marketplace: Opus 4 calls $0.20, Sonnet 5 calls $0.07, Haiku 11 calls $0.009. Pitch option (a) chosen: honest numbers, card-rail floor vs x402.
- 23:50 Review fixes landed: replayable settlement, Stripe reconcile, lenient decode, path validation. Local Postgres stays until the cloud switch.
- 00:05 Related-project research (5 readers + synthesis): integrate neither custos nor Deja Do. Borrowed: listing-text hygiene (length caps, no control or invisible characters), pitch positioning, two more 'what not to say' lines.
- 00:05 Third Armature dry run: agent fixed it itself without calling the marketplace. Two of three fresh runs skipped it; none bought. Consistent with the pitch's price argument.
- 09:05 README_AGENTS.md wheelhouse row now matches the fixture. Stale 23:28 runner stopped. Demo green after a server restart: B verify 4.2 s end to end and captured, C canceled, D refused; Stripe states match.
- 09:25 Deployed to Manufact at https://warm-wave-zjjim.run.mcp-use.com/mcp with Supabase and the laptop runner behind cloudflared. Full demo passed through it. Live dashboard in demo/dashboard.py.
- 09:57 Dashboard simplified, broken-fix beat and /present slides added. Published to https://github.com/julurisaichandu/reflex.
