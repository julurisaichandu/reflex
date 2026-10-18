# Stubs

Every stub is replaced before the demo unless explicitly approved.

| Stub | Where | Replaced by | Status |
|---|---|---|---|
| Payments return fake `pi_stub_*` ids; capture/cancel are no-ops | `server/payments.py` | Phase 2, Stripe test mode | replaced 23:27 (stub only when `STRIPE_SECRET_KEY` is empty) |
| Sandbox passes every test without running it | `server/sandbox.py` `run()` | Phase 1, Docker fixtures | replaced 23:17 |
| Local Postgres container (`reflex-pg`) instead of Supabase | `.env` `DATABASE_URL` | Supabase session pooler URI | replaced 09:20 (Supabase session pooler; full A-D demo verified on it) |
