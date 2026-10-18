# Reflex Exchange — MCP Tool Specification

Four tools. All inputs/outputs JSON. Implement with `mcp-use` (Python), deploy on Manufact.
Error shape everywhere: `{"error": {"code": string, "message": string, "retryable": bool}}`.

---

## 1. `publish_pack`

Seller agent publishes a ProofPack extracted from a successful execution.

**Input**
```json
{
  "title": "Fix pip ResolutionImpossible on pinned numpy/scipy conflict",
  "task_signature": "pip install fails: ResolutionImpossible numpy scipy",
  "description": "Resolves dependency conflict by relaxing pin and regenerating lockfile.",
  "trace": {
    "steps": [
      {"tool": "bash", "input": "pip install -r requirements.txt", "outcome": "error"},
      {"tool": "edit", "input": "requirements.txt: numpy==1.24.* -> numpy>=1.24,<2", "outcome": "ok"},
      {"tool": "bash", "input": "pip install -r requirements.txt", "outcome": "ok"}
    ],
    "solution_files": {"requirements.txt": "<full file contents>"}
  },
  "tests": [
    {"cmd": "pip install -r requirements.txt", "expect_exit": 0},
    {"cmd": "python -c 'import numpy, scipy'", "expect_exit": 0}
  ],
  "env_fingerprint": {
    "language": "python", "language_version": "3.11",
    "os": "linux", "package_manager": "pip",
    "key_deps": ["numpy", "scipy"]
  },
  "price_cents": 100,
  "seller_agent_id": "agent-a"
}
```

**Output**
```json
{
  "pack_id": "pk_7f3a",
  "status": "listed",
  "custos_status": "verified" ,
  "listing_url": "mcp://reflex-exchange/packs/pk_7f3a"
}
```
`custos_status` ∈ `verified | unverified | pending` — P2; default `"unverified"` until custos is wired. Validation: reject if `tests` empty or `trace.solution_files` empty.

---

## 2. `discover_packs`

Buyer agent searches for relevant packs. **Warnings matching the caller's fingerprint ride along — this is the Agent-D mechanism.**

**Input**
```json
{
  "task_description": "pip install failing with ResolutionImpossible on numpy",
  "env_fingerprint": {
    "language": "python", "language_version": "3.12",
    "os": "linux", "package_manager": "pnpm", "key_deps": ["numpy"]
  },
  "max_results": 5
}
```

**Output**
```json
{
  "packs": [
    {
      "pack_id": "pk_7f3a",
      "title": "Fix pip ResolutionImpossible on pinned numpy/scipy conflict",
      "description": "...",
      "price_cents": 100,
      "custos_status": "verified",
      "compatibility": [
        {"fingerprint_summary": "python3.11/pip/linux", "status": "pass", "observations": 2},
        {"fingerprint_summary": "python3.12/pnpm/linux", "status": "fail", "observations": 1}
      ],
      "warnings_for_your_env": [
        {
          "warning_id": "wn_01",
          "summary": "Verification failed on python3.12/pnpm: solution assumes pip lockfile; 1 canceled purchase.",
          "evidence": {"exit_code": 1, "error_class": "CommandNotFound: pip"},
          "created_at": "2026-10-18T05:40:00Z"
        }
      ],
      "recommendation": "not_recommended"
    }
  ]
}
```
`recommendation` ∈ `recommended | untested | not_recommended` — derived: any warning matching caller fingerprint → `not_recommended`; any pass on matching fingerprint → `recommended`; else `untested`. Matching = exact match on (language, language_version, package_manager); loosen only if demo needs it. Search: keyword/ILIKE on title+task_signature is fine for the demo; pgvector only if trivial.

---

## 3. `acquire_pack`

Creates the payment authorization. **Does NOT deliver the pack.**

**Input**
```json
{"pack_id": "pk_7f3a", "buyer_agent_id": "agent-b",
 "env_fingerprint": {"language": "python", "language_version": "3.11", "os": "linux", "package_manager": "pip", "key_deps": ["numpy","scipy"]}}
```

**Server behavior**
1. Look up pack; refuse if a warning exactly matches buyer fingerprint unless `"override_warning": true` (nice demo line for Agent C vs D).
2. `stripe.PaymentIntent.create(amount=100, currency="usd", capture_method="manual", payment_method="pm_card_visa", confirm=True)` → status `requires_capture`.
3. Insert transaction row, status `authorized`.

**Output**
```json
{
  "transaction_id": "tx_991",
  "payment_status": "authorized",
  "amount_cents": 100,
  "stripe_payment_intent_id": "pi_test_...",
  "next_step": "Call verify_and_settle with this transaction_id. The pack is delivered only after sandbox verification passes and payment is captured. If verification fails, your authorization is canceled automatically."
}
```

---

## 4. `verify_and_settle`

Runs the pack in a **marketplace-controlled Docker fixture** matching the buyer's fingerprint, then settles.

**Input**
```json
{"transaction_id": "tx_991"}
```

**Server behavior**
1. Load transaction (must be `authorized`), pack, buyer fingerprint → select fixture image (`py311-pip` | `py312-pnpm`); no fixture match → fail with `code: "no_fixture"` and cancel auth.
2. Run in Docker: apply `trace.solution_files`, run each test `cmd`. Constraints: `--network none --cpus 1 -m 512m`, 120s wall timeout, non-root, fixture mounted read-only, no secrets in env.
3. **All tests pass** → `stripe.PaymentIntent.capture(pi)` → transaction `captured` → insert verification row `pass` → **return full pack contents**.
4. **Any test fails / timeout** → `stripe.PaymentIntent.cancel(pi)` → transaction `canceled` → insert verification row `fail` with **redacted** evidence → insert warning row → return evidence only.

**Output (pass)**
```json
{
  "result": "pass",
  "payment": "captured",
  "pack": {
    "solution_files": {"requirements.txt": "<contents>"},
    "steps": ["Relax numpy pin to >=1.24,<2 in requirements.txt", "Re-run pip install"],
    "tests_passed": 2
  },
  "receipt": {"transaction_id": "tx_991", "amount_cents": 100, "stripe_payment_intent_id": "pi_test_..."}
}
```

**Output (fail)**
```json
{
  "result": "fail",
  "payment": "canceled",
  "evidence": {
    "fixture": "py312-pnpm",
    "failed_test": "pip install -r requirements.txt",
    "exit_code": 127,
    "error_class": "CommandNotFound",
    "note": "Pack contents withheld. Your authorization was canceled; you were not charged. A compatibility warning has been published for this environment."
  },
  "warning_id": "wn_01"
}
```

**Redaction rule (`redact.py`):** failure evidence may contain fixture name, failed test command, exit code, and a classified error type. It must NOT contain pack `solution_files`, diffs, or raw stdout/stderr (stderr → map to error_class via a small regex table; default `"UnknownError"`).
