import uuid

# Phase 0 stub (tracked in STUBS.md). Phase 2 replaces these with Stripe test-mode
# PaymentIntents: capture_method=manual, captured on PASS, canceled on FAIL.


def authorize(tx_id: str, amount_cents: int, description: str, metadata: dict) -> str:
    return f"pi_stub_{uuid.uuid4().hex[:12]}"


def capture(payment_intent_id: str, tx_id: str) -> None:
    pass


def cancel(payment_intent_id: str, tx_id: str) -> None:
    pass
