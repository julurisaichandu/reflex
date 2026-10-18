from pathlib import PurePosixPath

from server import db
from server.models import ToolError

MAX_FILES = 20
MAX_TOTAL_BYTES = 256 * 1024
MAX_TESTS = 10
MAX_CMD_CHARS = 1000


def _check_path(path: str) -> None:
    p = PurePosixPath(path)
    if not path or "\x00" in path or p.is_absolute() or ".." in p.parts or path.startswith("~") or path.endswith("/"):
        raise ToolError("invalid_pack", f"solution_files key {path!r} must be a relative path inside the repo.")


def run(pack: dict) -> dict:
    files = pack["trace"]["solution_files"]
    tests = pack["tests"]
    if not tests:
        raise ToolError("invalid_pack", "tests must contain at least one command that proves the solution works.")
    if not files:
        raise ToolError("invalid_pack", "trace.solution_files must contain at least one file.")
    if len(files) > MAX_FILES or sum(len(c.encode()) for c in files.values()) > MAX_TOTAL_BYTES:
        raise ToolError("invalid_pack", f"solution_files is limited to {MAX_FILES} files and {MAX_TOTAL_BYTES} bytes total.")
    if len(tests) > MAX_TESTS or any(len(t["cmd"]) > MAX_CMD_CHARS or not t["cmd"].strip() for t in tests):
        raise ToolError("invalid_pack", f"tests is limited to {MAX_TESTS} non-empty commands of at most {MAX_CMD_CHARS} characters.")
    for path in files:
        _check_path(path)
    if pack["price_cents"] < 50:
        raise ToolError("invalid_pack", "price_cents must be at least 50 (the Stripe minimum charge).")

    with db.connect() as conn:
        db.ensure_agent(conn, pack["seller_agent_id"])
        pack_id = db.insert_pack(conn, pack)
    return {
        "pack_id": pack_id,
        "status": "listed",
        "custos_status": "unverified",
        "listing_url": f"mcp://reflex-exchange/packs/{pack_id}",
    }
