import functools
import logging
import os
import uuid

import stripe

log = logging.getLogger("reflex.payments")


class PaymentError(Exception):
    pass


@functools.cache
def _client() -> stripe.StripeClient | None:
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        log.warning("STRIPE_SECRET_KEY is not set: payments are STUBBED (see STUBS.md)")
        return None
    if not key.startswith(("sk_test_", "rk_test_")):
        raise RuntimeError("Reflex Exchange runs in Stripe test mode only; STRIPE_SECRET_KEY must be a test key.")
    return stripe.StripeClient(key)


def authorize(tx_id: str, amount_cents: int, description: str, metadata: dict) -> str:
    client = _client()
    if client is None:
        return f"pi_stub_{uuid.uuid4().hex[:12]}"
    try:
        pi = client.v1.payment_intents.create(
            params={
                "amount": amount_cents,
                "currency": "usd",
                "capture_method": "manual",
                "payment_method": "pm_card_visa",
                "payment_method_types": ["card"],
                "confirm": True,
                "description": description,
                "metadata": metadata,
            },
            options={"idempotency_key": f"authorize-{tx_id}"},
        )
    except stripe.StripeError as e:
        raise PaymentError(f"authorize {tx_id}: {e.user_message or type(e).__name__}") from e
    if pi.status != "requires_capture":
        raise PaymentError(f"authorize {tx_id}: PaymentIntent {pi.id} is {pi.status}, expected requires_capture")
    return pi.id


def capture(payment_intent_id: str, tx_id: str) -> None:
    client = _client()
    if client is None:
        return
    try:
        pi = client.v1.payment_intents.capture(payment_intent_id, options={"idempotency_key": f"capture-{tx_id}"})
    except stripe.StripeError as e:
        raise PaymentError(f"capture {tx_id}: {type(e).__name__}") from e
    if pi.status != "succeeded":
        raise PaymentError(f"capture {tx_id}: PaymentIntent {pi.id} is {pi.status}, expected succeeded")


def cancel(payment_intent_id: str, tx_id: str) -> None:
    client = _client()
    if client is None:
        return
    try:
        pi = client.v1.payment_intents.cancel(payment_intent_id, options={"idempotency_key": f"cancel-{tx_id}"})
    except stripe.StripeError as e:
        raise PaymentError(f"cancel {tx_id}: {type(e).__name__}") from e
    if pi.status != "canceled":
        raise PaymentError(f"cancel {tx_id}: PaymentIntent {pi.id} is {pi.status}, expected canceled")
