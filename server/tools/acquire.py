import uuid

from server import db, payments
from server.models import ToolError, summary

NEXT_STEP = (
    "Call verify_and_settle with this transaction_id. The pack is delivered only after sandbox verification "
    "passes and payment is captured. If verification fails, your authorization is canceled automatically."
)


def run(pack_id: str, buyer_agent_id: str, fp: dict, override_warning: bool) -> dict:
    with db.connect() as conn:
        pack = db.get_pack(conn, pack_id)
        if pack is None:
            raise ToolError("pack_not_found", f"No pack with id {pack_id!r}. Use discover_packs to find pack ids.")
        warnings = db.matching_warnings(conn, [pack_id], fp)
        if warnings and not override_warning:
            raise ToolError(
                "warning_exists",
                f"{len(warnings)} recorded failure(s) match your environment ({summary(fp)}). "
                f"Latest: {warnings[0]['summary']} Pass override_warning=true to buy anyway; "
                "you are still charged only if verification passes.",
            )
        db.ensure_agent(conn, buyer_agent_id)

    tx_id = f"tx_{uuid.uuid4().hex[:8]}"
    pi_id = payments.authorize(
        tx_id,
        pack["price_cents"],
        f"Reflex Exchange ProofPack {pack_id}",
        {"transaction_id": tx_id, "pack_id": pack_id, "buyer_agent_id": buyer_agent_id},
    )
    try:
        with db.connect() as conn:
            db.insert_transaction(conn, {
                "id": tx_id,
                "pack_id": pack_id,
                "buyer_agent_id": buyer_agent_id,
                "buyer_env_fingerprint": fp,
                "stripe_payment_intent_id": pi_id,
                "amount_cents": pack["price_cents"],
            })
    except Exception:
        payments.cancel(pi_id, tx_id)
        raise
    return {
        "transaction_id": tx_id,
        "payment_status": "authorized",
        "amount_cents": pack["price_cents"],
        "stripe_payment_intent_id": pi_id,
        "next_step": NEXT_STEP,
    }
