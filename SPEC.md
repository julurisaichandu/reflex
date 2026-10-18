# Reflex Exchange — Locked Build Spec

**Tagline:** *The marketplace sells successes and gives away failures.*

**One-liner:** A marketplace where AI agents sell verified ProofPacks (reproducible, test-backed solutions extracted from successful execution traces). Buyers pay via test-mode Stripe with manual capture; verification runs in a marketplace-controlled sandbox before delivery; failed verifications cancel payment and publish a free compatibility warning that future agents see before buying.

**Event:** "Make Something Agents Want" hackathon, YC SF, Oct 17–18 2026.
**Submission deadline:** Sun 10:00 AM. **Backup demo video due:** 8:00 AM (hard internal deadline).
**Prize targets:** Manufact (best MCP server), Armature (agents self-onboard, no human in loop), Blaxel one-liner track, YC overall.

---

## Architecture

```
Seller Agent A                    Marketplace (MCP server on Manufact)              Buyer Agents B/C/D
     │                                        │                                          │
     │ publish(trace,tests,fingerprint,price) │                                          │
     ├───────────────────────────────────────►│  store pack (Supabase)                   │
     │                                        │  [P2] custos notarization badge          │
     │                                        │                                          │
     │                                        │◄──────────── discover(task, fingerprint) ┤
     │                                        │  returns listings + compat matrix        │
     │                                        │  + WARNINGS matching caller fingerprint  │
     │                                        │                                          │
     │                                        │◄──────────── acquire(pack_id, fp) ───────┤
     │                                        │  Stripe PaymentIntent $1.00,             │
     │                                        │  capture_method=manual → authorized      │
     │                                        │                                          │
     │                                        │◄──────────── verify(transaction_id) ─────┤
     │                                        │  run pack in MARKETPLACE Docker fixture  │
     │                                        │  matching buyer fingerprint              │
     │                                        │    PASS → capture payment → deliver pack │
     │                                        │    FAIL → cancel auth → redacted         │
     │                                        │           evidence → publish warning     │
```

### Non-negotiable design rules
1. **Deliver after capture, never before.** The pack's usable contents are returned only after a sandbox PASS and successful Stripe capture. On FAIL the buyer receives only redacted evidence (fingerprint, exit code, sanitized error class) — never raw sandbox logs, never pack contents.
2. **Marketplace-controlled sandbox.** Verification runs in the marketplace's Docker, not the buyer's machine. Fingerprints describe environments; **fixtures reproduce them** — a small set of pre-built Docker images (e.g. `py311-pip`, `py312-pnpm-node20`) keyed by fingerprint.
3. **Seller code is untrusted.** Sandbox runs with: `--network none`, `--cpus 1`, `-m 512m`, 120s timeout, non-root user, read-only fixture mount, no env secrets.
4. **Warnings are a byproduct, not a feature.** A failed verification auto-inserts a warning row keyed to the env fingerprint. `discover` surfaces matching warnings — that's the whole Agent-D mechanism. No separate warnings API.
5. **Stripe constraints:** test mode only, $1.00 price (min charge $0.50), `capture_method=manual`, platform-only (no Connect/payouts). Pitch language: "Stripe-based, x402-shaped" — do not claim x402 compliance.
6. **Demo-driven scope:** every component must serve the A→B→C→D demo. Anything else waits.

---

## Priorities

| Priority | Deliverable |
|---|---|
| P0 | Four working MCP tools end-to-end (stub payment+sandbox first, then replace) |
| P0 | Marketplace-controlled Docker verification against fixtures |
| P0 | Stripe test-mode authorize → capture / cancel |
| P0 | Success & failure stored as evidence (transactions + verifications tables) |
| P1 | Compatibility matrix + warnings surfaced in `discover` |
| P1 | Agent-facing README/skill (Armature deliverable — see README_AGENTS.md) |
| P1 | **Backup demo video recorded by 8 AM** |
| P2 | Deja Do trace extraction; custos notarization badge |
| Stretch | Blaxel sandbox deployment; Primitive email on failure; seller agent on InstaBox |

**45-minute rule:** any integration that fights back for >45 min gets stubbed and narrated in the demo. A working loop at 6 AM beats four half-integrations at 9:55.

---

## Demo script (3 minutes)

| Beat | What's on screen | Line |
|---|---|---|
| 0:00 | Agent A grinding through a real repo bug — tool-call + cost counter running | "Agent A just spent 37 tool calls and $0.42 fixing this." |
| 0:40 | `publish` → pack listed, (custos badge if P2 done) | "It packages that experience as a ProofPack and lists it for $1." |
| 1:00 | Agent B, *variant* repo → `discover` → `acquire` → 402/authorize → sandbox PASS → capture → delivery → solves in ~5 calls | "Agent B pays a dollar, the marketplace verifies it in a sandbox first, and B solves it in 5 calls. Side by side: tokens, dollars, minutes saved." |
| 1:50 | Agent C, incompatible env (py3.12 fixture) → authorize → sandbox FAIL → **auth canceled** (Stripe dashboard visible) → warning row appears | "Agent C's environment is incompatible. Verification fails, the payment is canceled — and the failure becomes free public knowledge." |
| 2:20 | Agent D, same env as C → `discover` returns listing **with warning** before any payment | "Agent D asks about the same task and is warned off before spending anything. The market is accumulating intelligence, not just recording transactions." |
| 2:45 | Tagline card | "Reflex Exchange: the marketplace sells successes and gives away failures. Every success transfers experience; every failure teaches the whole network. Eighteen months ago no agent had a credit card. Tonight one agent paid another for experience — and got its money back when it didn't fit." |

---

## Repo layout

```
reflex-exchange/
├── server/
│   ├── main.py              # MCP server (mcp-use), registers 4 tools
│   ├── tools/
│   │   ├── publish.py
│   │   ├── discover.py
│   │   ├── acquire.py
│   │   └── verify.py
│   ├── payments.py          # Stripe PaymentIntent authorize/capture/cancel
│   ├── sandbox.py           # Docker fixture runner (untrusted-code constraints)
│   ├── db.py                # Supabase client + queries
│   └── redact.py            # failure-evidence sanitizer
├── fixtures/
│   ├── py311-pip/Dockerfile
│   └── py312-pnpm/Dockerfile
├── demo/
│   ├── seller_agent.md      # prompt/script for Agent A
│   ├── buyer_agent.md       # prompt/script for Agents B/C/D
│   └── repos/               # bug repo + variant + incompatible variant
├── supabase_schema.sql
├── README_AGENTS.md         # agent-facing onboarding (Armature deliverable)
└── SPEC.md                  # this file
```
