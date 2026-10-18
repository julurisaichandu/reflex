from server import db
from server.models import match_key, summary


def _status(row: dict) -> str:
    if row["fails"] == 0:
        return "pass"
    return "fail" if row["passes"] == 0 else "mixed"


def run(task_description: str, fp: dict, max_results: int) -> dict:
    limit = max(1, min(max_results, 20))
    with db.connect() as conn:
        packs = db.search_packs(conn, task_description, limit)
        ids = [p["id"] for p in packs]
        compat = db.compatibility(conn, ids) if ids else []
        warnings = db.matching_warnings(conn, ids, fp) if ids else []

    results = []
    for p in packs:
        rows = [r for r in compat if r["pack_id"] == p["id"]]
        mine = [w for w in warnings if w["pack_id"] == p["id"]]
        passed_here = any(match_key(r) == match_key(fp) and r["passes"] > 0 for r in rows)
        results.append({
            "pack_id": p["id"],
            "title": p["title"],
            "description": p["description"],
            "price_cents": p["price_cents"],
            "custos_status": p["custos_status"],
            "compatibility": [
                {
                    # Every sandbox fixture is Linux, so observed environments are too.
                    "fingerprint_summary": summary({**r, "os": "linux"}),
                    "status": _status(r),
                    "observations": r["passes"] + r["fails"],
                }
                for r in rows
            ],
            "warnings_for_your_env": [
                {
                    "warning_id": w["id"],
                    "summary": w["summary"],
                    "evidence": w["evidence"],
                    "created_at": w["created_at"].isoformat(),
                }
                for w in mine
            ],
            "recommendation": "not_recommended" if mine else "recommended" if passed_here else "untested",
        })
    return {"packs": results}
