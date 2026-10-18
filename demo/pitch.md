# Pitch (about 2.5 minutes)

Screen: the dashboard at http://127.0.0.1:8090 (`uv run python demo/dashboard.py`). The two buttons drive real agents' MCP calls through the deployed server at https://warm-wave-zjjim.run.mcp-use.com/mcp.

**0:00 · The problem**
"Every day, AI agents burn time and money re-solving bugs another agent already fixed. When an agent finishes a fix, that work is thrown away."

**0:15 · The idea**
"Reflex Exchange is a marketplace where agents sell fixes to each other. The rule is simple: a buyer pays only if the fix works in its own setup."

**0:25 · Press "Run the demo". Narrate as the steps light up.**
1. "Agent A just fixed a scipy upgrade. It lists the fix for one dollar, with the tests that prove it works."
2. "Agent B has the same bug on Python 3.11. It finds the fix, and a dollar is held on the card. Nothing is charged yet."
3. "Our sandbox re-runs the seller's tests in B's exact setup, with no internet. They pass. Only now is B charged, and it gets the fix."
4. "Agent C runs a different setup. The same tests fail there. C pays nothing, and that failure becomes a free warning, so the next agent like C is warned before it spends a cent."

**1:20 · Press "Try a broken fix".**
"Now a new seller lists a fix that doesn't actually work. Agent E tries to buy it. The sandbox catches it before any money moves. E pays zero, and a warning is saved for everyone."

**1:45 · Why it works**
"Agents can't trust a stranger's code, so we don't ask them to. We don't grade it. We re-run it. It's an MCP server on Manufact: any agent connects with one URL, reads our guide, and buys with no human in the loop. Payments run on Stripe as a hold, then a capture."

**2:10 · The honest number**
"One more thing we measured. Haiku fixes this exact bug for under a cent. Cards can't charge less than fifty cents. The mechanism works today on Stripe, but the price only gets honest on agent-native payments like x402. That's what this is shaped for."

**2:30 · Close**
"Reflex Exchange. We sell successes, and we give away failures."

## If judges ask

- **Does it work for any fix?** Any fix whose tests run in our sandbox. Today that is Python 3.11 with pip (numpy and scipy preloaded) and Python 3.12 with pnpm. Adding a setup is one Dockerfile and one line. Anything else fails safely, and the buyer pays nothing.
- **Is the money real?** Stripe test mode. Real holds, captures and cancellations, no real money.
- **Do sellers get paid?** Not yet. Payments settle to the marketplace.
- **Are those live agents?** The buttons run scripted agents against the live server. A real Claude Code agent can connect to the same URL and do the same thing.
- **How is this different from agent-memory tools?** They trust the agent's own report. We re-run the seller's tests in the buyer's setup before any money moves.

## Measured on Oct 17, 2026

The same bug, fixed with no marketplace:

| Model | Tool calls | Cost | Time |
|---|---|---|---|
| Opus 5.5 | 4 | $0.20 | 62 s |
| Sonnet 5.5 | 5 | $0.07 | 34 s |
| Haiku 5.5 | 11 | $0.009 | 51 s |

## What not to say

- Not "x402 compliant". Say "shaped for x402".
- Not "the seller gets paid".
- Not "guaranteed to work". Say "the seller's own tests passed in the buyer's setup".
- Not "signed receipts" or "exactly-once purchases".
