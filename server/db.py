import os
import re
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

# Listing columns only. Pack contents (trace, tests) are read solely by verify_and_settle.
LISTING = "id, seller_agent_id, title, task_signature, description, env_fingerprint, price_cents, custos_status, created_at"
MATCHES_FP = (
    "env_fingerprint->>'language' = %(language)s"
    " and env_fingerprint->>'language_version' = %(language_version)s"
    " and env_fingerprint->>'package_manager' = %(package_manager)s"
)


@contextmanager
def connect():
    # prepare_threshold=None keeps psycopg compatible with Supabase's pgbouncer-style poolers.
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row, prepare_threshold=None) as conn:
        yield conn


def ensure_agent(conn, agent_id: str) -> None:
    conn.execute(
        "insert into agents (id, display_name) values (%s, %s) on conflict (id) do nothing",
        (agent_id, agent_id),
    )


def insert_pack(conn, pack: dict) -> str:
    row = conn.execute(
        """insert into packs (seller_agent_id, title, task_signature, description, trace, tests, env_fingerprint, price_cents)
           values (%(seller_agent_id)s, %(title)s, %(task_signature)s, %(description)s,
                   %(trace)s, %(tests)s, %(env_fingerprint)s, %(price_cents)s)
           returning id""",
        {
            **pack,
            "trace": Jsonb(pack["trace"]),
            "tests": Jsonb(pack["tests"]),
            "env_fingerprint": Jsonb(pack["env_fingerprint"]),
        },
    ).fetchone()
    return row["id"]


def search_packs(conn, text: str, limit: int) -> list[dict]:
    terms = re.findall(r"[a-z0-9]+", text.lower())
    if not terms:
        return conn.execute(f"select {LISTING} from packs order by created_at desc limit %s", (limit,)).fetchall()
    return conn.execute(
        f"""select {LISTING} from packs, to_tsquery('english', %(q)s) q
            where to_tsvector('english', title || ' ' || task_signature) @@ q
            order by ts_rank(to_tsvector('english', title || ' ' || task_signature), q) desc, created_at desc
            limit %(limit)s""",
        {"q": " | ".join(terms), "limit": limit},
    ).fetchall()


def get_pack(conn, pack_id: str, *, with_contents: bool = False) -> dict | None:
    cols = LISTING + (", trace, tests" if with_contents else "")
    return conn.execute(f"select {cols} from packs where id = %s", (pack_id,)).fetchone()


def compatibility(conn, pack_ids: list[str]) -> list[dict]:
    return conn.execute(
        "select * from pack_compatibility where pack_id = any(%s) order by last_observed desc", (pack_ids,)
    ).fetchall()


def matching_warnings(conn, pack_ids: list[str], fp: dict) -> list[dict]:
    return conn.execute(
        f"""select id, pack_id, summary, evidence, created_at from warnings
            where pack_id = any(%(ids)s) and {MATCHES_FP} order by created_at desc""",
        {"ids": pack_ids, **fp},
    ).fetchall()


def insert_transaction(conn, tx: dict) -> None:
    conn.execute(
        """insert into transactions (id, pack_id, buyer_agent_id, buyer_env_fingerprint, stripe_payment_intent_id, amount_cents)
           values (%(id)s, %(pack_id)s, %(buyer_agent_id)s, %(buyer_env_fingerprint)s, %(stripe_payment_intent_id)s, %(amount_cents)s)""",
        {**tx, "buyer_env_fingerprint": Jsonb(tx["buyer_env_fingerprint"])},
    )


def get_transaction(conn, tx_id: str) -> dict | None:
    return conn.execute("select * from transactions where id = %s", (tx_id,)).fetchone()


def resolve_transaction(conn, tx_id: str, status: str) -> None:
    row = conn.execute(
        "update transactions set status = %s, resolved_at = now() where id = %s and status = 'authorized' returning id",
        (status, tx_id),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"transaction {tx_id} left the authorized state during settlement")


def insert_verification(conn, v: dict) -> str:
    return conn.execute(
        """insert into verifications (transaction_id, pack_id, fixture, env_fingerprint, result, evidence, duration_ms)
           values (%(transaction_id)s, %(pack_id)s, %(fixture)s, %(env_fingerprint)s, %(result)s, %(evidence)s, %(duration_ms)s)
           returning id""",
        {**v, "env_fingerprint": Jsonb(v["env_fingerprint"]), "evidence": Jsonb(v["evidence"])},
    ).fetchone()["id"]


def latest_verification(conn, tx_id: str) -> dict | None:
    return conn.execute(
        "select id, result, evidence from verifications where transaction_id = %s order by created_at desc limit 1",
        (tx_id,),
    ).fetchone()


def warning_for(conn, verification_id: str) -> str | None:
    row = conn.execute("select id from warnings where verification_id = %s", (verification_id,)).fetchone()
    return row and row["id"]


def insert_warning(conn, w: dict) -> str:
    return conn.execute(
        """insert into warnings (pack_id, verification_id, env_fingerprint, summary, evidence)
           values (%(pack_id)s, %(verification_id)s, %(env_fingerprint)s, %(summary)s, %(evidence)s)
           returning id""",
        {**w, "env_fingerprint": Jsonb(w["env_fingerprint"]), "evidence": Jsonb(w["evidence"])},
    ).fetchone()["id"]
