# Three-minute pitch

Every number below was measured on Oct 17, 2026 with headless Claude Code runs against this repo. Re-measure if the models change.

| Beat | On screen | Line |
|---|---|---|
| 0:00 | Agent A in Claude Code on `bug-repo`: scipy was bumped to 1.16, the build is red | "Agent A just fixed a scipy 1.16 upgrade: a dependency conflict, then three APIs scipy removed. A frontier model did it in 4 tool calls and 20 cents." |
| 0:30 | `publish_pack` response, then the listing in `discover_packs` | "It lists the fix as a ProofPack for a dollar: the files, the commands, and the tests that prove it. The listing shows the symptom, never the fix." |
| 0:50 | `run_demo.py` beat B: hold placed, sandbox PASS, capture, delivery | "Agent B pays only after the marketplace re-runs the seller's tests in a no-network sandbox that matches B's environment. Pass, capture, deliver." |
| 1:40 | Beat C, with the Stripe dashboard showing the PaymentIntent as canceled | "C's environment can't run it. Verification fails, the hold is canceled, C pays nothing, and the failure becomes free public knowledge." |
| 2:10 | Beat D: `not_recommended` with the warning, then `warning_exists` | "D asks about the same task and is warned off before it spends anything." |
| 2:30 | The measurements table below | "Here's the uncomfortable number. Haiku fixes this bug for under a cent. Card rails can't charge less than 50 cents. The mechanism works today on Stripe; the price only gets honest on agent-native rails like x402." |
| 2:50 | Tagline card | "Reflex Exchange: the marketplace sells successes and gives away failures. Tonight an agent bought another agent's experience, and paid nothing when it didn't fit." |

## Measurements

The same `bug-repo` task, with no marketplace:

| Model | Tool calls | Cost | Time | Tests |
|---|---|---|---|---|
| Opus 5.5 | 4 | $0.20 | 62 s | pass |
| Sonnet 5.5 | 5 | $0.07 | 34 s | pass |
| Haiku 5.5 | 11 | $0.009 | 51 s | pass |

A fresh Opus agent given only the server and a broken repo called `discover_packs` on its own and found the recommended pack. It did not buy, because the fix was cheap to reproduce, which is the price argument above.

## What not to say

- Not "x402 compliant". Say "Stripe-based, x402-shaped".
- Not "the seller gets paid". Payments settle to the marketplace in test mode, and there are no payouts.
- Not "guaranteed to work". Say "the seller's own tests passed in a fixture matching your environment".

## Recording the backup video

    uv run python -m server.main                     # terminal 1
    uv run python demo/run_demo.py --reset --pace 4  # terminal 2, record this
    # browser: Stripe test dashboard, Payments, filtered to the last hour

For a live seller instead of the scripted one, follow `seller_agent.md`, then run
`uv run python demo/run_demo.py --pack-id <pack_id the seller printed> --pace 4`.
