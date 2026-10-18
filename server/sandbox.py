import os
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from server.models import match_key

# Fingerprints describe environments; fixtures reproduce them.
FIXTURES = {
    ("python", "3.11", "pip"): "py311-pip",
    ("python", "3.12", "pnpm"): "py312-pnpm",
}
IMAGE_PREFIX = "reflex-fixture/"
TIMEOUT_S = 120
OUTPUT_TAIL_BYTES = 8192

# Seller code is untrusted: no network, 1 CPU, 512 MB with no swap, non-root, read-only image,
# read-only pack mount, scratch on tmpfs, no capabilities, and no env beyond the fixture image's.
SANDBOX_FLAGS = [
    "--network", "none",
    "--cpus", "1",
    "--memory", "512m",
    "--memory-swap", "512m",
    "--pids-limit", "256",
    "--cap-drop", "ALL",
    "--security-opt", "no-new-privileges",
    "--user", "10001:10001",
    "--read-only",
    "--tmpfs", "/work:rw,exec,nosuid,size=400m,uid=10001,gid=10001",
    "--tmpfs", "/tmp:rw,exec,nosuid,size=64m,uid=10001,gid=10001",
    "--workdir", "/work",
    "--label", "reflex.sandbox=1",
    "--pull", "never",
]

# Test output stays on the container's tmpfs; only a bounded tail comes back, for error classification.
RUN_TEST = (
    'sh -c "$1" >/tmp/.reflex-out 2>/tmp/.reflex-err; code=$?; '
    f"tail -c {OUTPUT_TAIL_BYTES} /tmp/.reflex-out; tail -c {OUTPUT_TAIL_BYTES} /tmp/.reflex-err >&2; exit $code"
)


class SandboxUnavailable(Exception):
    pass


def fixture_for(fp: dict) -> str | None:
    return FIXTURES.get(match_key(fp))


@dataclass
class TestRun:
    cmd: str
    expect_exit: int
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return not self.timed_out and self.exit_code == self.expect_exit


@dataclass
class SandboxResult:
    fixture: str
    runs: list[TestRun] = field(default_factory=list)
    duration_ms: int = 0

    @property
    def failed_run(self) -> TestRun | None:
        return next((r for r in self.runs if not r.ok), None)

    @property
    def passed(self) -> bool:
        return bool(self.runs) and self.failed_run is None


def _write_pack(root: Path, solution_files: dict[str, str]) -> None:
    os.chmod(root, 0o755)
    for rel, content in solution_files.items():
        path = root / rel
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"solution file escapes the pack root: {rel!r}")
        path.parent.mkdir(parents=True, exist_ok=True)
        for parent in path.relative_to(root).parents:
            os.chmod(root / parent, 0o755)
        path.write_text(content)
        os.chmod(path, 0o644)


def _docker(*args: str, timeout: float) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


def run(fixture: str, solution_files: dict[str, str], tests: list[dict]) -> SandboxResult:
    start = time.monotonic()
    deadline = start + TIMEOUT_S
    name = f"reflex-sbx-{uuid.uuid4().hex[:12]}"
    runs: list[TestRun] = []
    with tempfile.TemporaryDirectory(prefix="reflex-pack-") as tmp:
        _write_pack(Path(tmp), solution_files)
        try:
            started = _docker(
                "run", "-d", "--name", name, *SANDBOX_FLAGS,
                "--mount", f"type=bind,src={tmp},dst=/pack,readonly",
                IMAGE_PREFIX + fixture, "sleep", str(TIMEOUT_S + 30),
                timeout=60,
            )
            if started.returncode != 0:
                raise SandboxUnavailable(f"docker run {fixture} failed: {started.stderr.strip()[:500]}")
            copied = _docker("exec", name, "cp", "-R", "/pack/.", "/work/", timeout=30)
            if copied.returncode != 0:
                raise SandboxUnavailable(f"copying the pack into {fixture} failed: {copied.stderr.strip()[:500]}")
            for test in tests:
                remaining = deadline - time.monotonic()
                try:
                    if remaining <= 0:
                        raise subprocess.TimeoutExpired(test["cmd"], 0)
                    p = _docker("exec", name, "sh", "-c", RUN_TEST, "reflex-test", test["cmd"], timeout=remaining)
                    result = TestRun(test["cmd"], test["expect_exit"], p.returncode, p.stdout, p.stderr)
                except subprocess.TimeoutExpired:
                    result = TestRun(test["cmd"], test["expect_exit"], -1, timed_out=True)
                runs.append(result)
                if not result.ok:
                    break
        except (OSError, subprocess.TimeoutExpired) as e:
            raise SandboxUnavailable(f"docker unavailable: {e}") from e
        finally:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=60)
    return SandboxResult(fixture=fixture, runs=runs, duration_ms=int((time.monotonic() - start) * 1000))
