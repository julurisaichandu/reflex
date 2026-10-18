from dataclasses import dataclass, field

from server.models import match_key

# Fingerprints describe environments; fixtures reproduce them.
FIXTURES = {
    ("python", "3.11", "pip"): "py311-pip",
    ("python", "3.12", "pnpm"): "py312-pnpm",
}


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


def run(fixture: str, solution_files: dict[str, str], tests: list[dict]) -> SandboxResult:
    # Phase 0 stub (tracked in STUBS.md): every test passes without executing.
    runs = [TestRun(cmd=t["cmd"], expect_exit=t["expect_exit"], exit_code=t["expect_exit"]) for t in tests]
    return SandboxResult(fixture=fixture, runs=runs)
