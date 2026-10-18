import logging
import threading
from contextlib import contextmanager

from server import db, payments, redact, sandbox
from server.models import ToolError, summary

log = logging.getLogger("reflex.verify")

FAIL_NOTE = (
    "Pack contents withheld. Your authorization was canceled; you were not charged. "
    "A compatibility warning has been published for this environment."
)

# ponytail: per-process claim; running several server instances needs a DB advisory lock instead.
_claimed: set[str] = set()
_claim_lock = threading.Lock()


@contextmanager
def _claim(tx_id: str):
    with _claim_lock:
        if tx_id in _claimed:
            raise ToolError("verification_in_progress", f"{tx_id} is already being verified. Retry shortly.", retryable=True)
        _claimed.add(tx_id)
    try:
        yield
    finally:
        with _claim_lock:
            _claimed.discard(tx_id)


def _delivery(tx: dict, pack: dict) -> dict:
    return {
        "result": "pass",
        "payment": "captured",
        "pack": {
            "solution_files": pack["trace"]["solution_files"],
            "steps": [f"{s['tool']}: {s['input']} ({s['outcome']})" for s in pack["trace"]["steps"]],
            "tests": pack["tests"],
            "tests_passed": len(pack["tests"]),
        },
        "receipt": {
            "transaction_id": tx["id"],
            "amount_cents": tx["amount_cents"],
            "stripe_payment_intent_id": tx["stripe_payment_intent_id"],
        },
    }


def _settled(conn, tx: dict, pack: dict) -> dict:
    # Settlement is replayable: a buyer whose response was lost calls again and gets the same outcome.
    if tx["status"] == "captured":
        return _delivery(tx, pack)
    v = db.latest_verification(conn, tx["id"])
    return {
        "result": "fail",
        "payment": "canceled",
        "evidence": {**(v["evidence"] if v else {}), "note": "Your authorization was canceled; you were not charged."},
        "warning_id": v and db.warning_for(conn, v["id"]),
    }


def _cancel(tx_id: str, pi_id: str) -> None:
    with db.connect() as conn:
        db.resolve_transaction(conn, tx_id, "canceled")
        payments.cancel(pi_id, tx_id)


def run(tx_id: str) -> dict:
    with _claim(tx_id):
        with db.connect() as conn:
            tx = db.get_transaction(conn, tx_id)
            if tx is None:
                raise ToolError("transaction_not_found", f"No transaction with id {tx_id!r}. Use the id acquire_pack returned.")
            pack = db.get_pack(conn, tx["pack_id"], with_contents=True)
            if tx["status"] != "authorized":
                return _settled(conn, tx, pack)
        fp = tx["buyer_env_fingerprint"]
        pi_id = tx["stripe_payment_intent_id"]

        # Stripe is the source of truth for money: an earlier attempt may have captured or canceled
        # before its database write was lost.
        status = payments.status(pi_id)
        if status == "succeeded":
            with db.connect() as conn:
                db.resolve_transaction(conn, tx_id, "captured")
            return _delivery(tx, pack)
        if status == "canceled":
            with db.connect() as conn:
                db.resolve_transaction(conn, tx_id, "canceled")
            raise ToolError("not_authorized_state", f"The authorization for {tx_id} was already canceled; you were not charged.")

        fixture = sandbox.fixture_for(fp)
        if fixture is None:
            _cancel(tx_id, pi_id)
            raise ToolError(
                "no_fixture",
                f"No sandbox fixture reproduces {summary(fp)} (available: {', '.join(sorted(sandbox.FIXTURES.values()))}). "
                "Your authorization was canceled; you were not charged.",
            )

        try:
            result = sandbox.run(fixture, pack["trace"]["solution_files"], pack["tests"])
        except sandbox.SandboxUnavailable:
            log.exception("sandbox unavailable for %s", tx_id)
            raise ToolError(
                "sandbox_unavailable",
                "The verification sandbox is temporarily unavailable. Your authorization is still held and nothing "
                "was charged. Retry verify_and_settle shortly.",
                retryable=True,
            )
        except Exception:
            log.exception("sandbox error for %s", tx_id)
            _cancel(tx_id, pi_id)
            raise ToolError(
                "verification_error",
                "The marketplace could not run this pack's verification. Your authorization was canceled; you were not charged.",
            )

        verification = {
            "transaction_id": tx_id,
            "pack_id": pack["id"],
            "fixture": fixture,
            "env_fingerprint": fp,
            "duration_ms": result.duration_ms,
        }

        if result.passed:
            # Database writes commit only after Stripe confirms, so a database failure surfaces before money moves.
            try:
                with db.connect() as conn:
                    db.resolve_transaction(conn, tx_id, "captured")
                    db.insert_verification(conn, {
                        **verification,
                        "result": "pass",
                        "evidence": {"fixture": fixture, "tests_passed": len(result.runs)},
                    })
                    payments.capture(pi_id, tx_id)
            except payments.PaymentError:
                log.exception("capture failed for %s", tx_id)
                raise ToolError(
                    "capture_failed",
                    "Verification passed but payment capture failed, so the pack was not delivered. "
                    "Retry verify_and_settle.",
                    retryable=True,
                )
            # Deliver after capture, never before.
            return _delivery(tx, pack)

        evidence = redact.evidence(fixture, result.failed_run)
        with db.connect() as conn:
            db.resolve_transaction(conn, tx_id, "canceled")
            vf_id = db.insert_verification(conn, {**verification, "result": "fail", "evidence": evidence})
            wn_id = db.insert_warning(conn, {
                "pack_id": pack["id"],
                "verification_id": vf_id,
                "env_fingerprint": fp,
                "summary": (
                    f"Verification failed on {summary(fp)}: `{evidence['failed_test']}` "
                    f"exited {evidence['exit_code']} ({evidence['error_class']}). The buyer's payment was canceled."
                ),
                "evidence": evidence,
            })
            payments.cancel(pi_id, tx_id)
        return {"result": "fail", "payment": "canceled", "evidence": {**evidence, "note": FAIL_NOTE}, "warning_id": wn_id}
