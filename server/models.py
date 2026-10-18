import re

from pydantic import BaseModel, Field, field_validator


class ToolError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable

    def payload(self) -> dict:
        return {"error": {"code": self.code, "message": self.message, "retryable": self.retryable}}


class EnvFingerprint(BaseModel):
    language: str = Field(description='Lowercase language name, e.g. "python".')
    language_version: str = Field(description='major.minor, e.g. "3.11". A patch suffix ("3.11.9") is dropped.')
    os: str = Field(default="linux", description='e.g. "linux".')
    package_manager: str = Field(description='The tool that installs dependencies, e.g. "pip" or "pnpm".')
    key_deps: list[str] = Field(default_factory=list, description='Packages central to the task, e.g. ["numpy", "scipy"].')

    @field_validator("language", "os", "package_manager")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("language_version")
    @classmethod
    def _major_minor(cls, v: str) -> str:
        m = re.match(r"\s*v?(\d+)\.(\d+)", v)
        return f"{m[1]}.{m[2]}" if m else v.strip()

    @field_validator("key_deps")
    @classmethod
    def _deps(cls, v: list[str]) -> list[str]:
        return sorted({d.strip().lower() for d in v if d.strip()})


class TraceStep(BaseModel):
    tool: str = Field(description='Tool you called, e.g. "bash" or "edit".')
    input: str = Field(description="What you ran or changed.")
    outcome: str = Field(description='"ok" or "error".')


class Trace(BaseModel):
    steps: list[TraceStep] = Field(description="The steps from your successful run, in order.")
    solution_files: dict[str, str] = Field(
        description="Relative path -> full file contents. Written verbatim into the sandbox workdir. Must be self-contained: the sandbox has no network."
    )


class PackTest(BaseModel):
    cmd: str = Field(description='Shell command run in the sandbox workdir, e.g. "pip install -r requirements.txt".')
    expect_exit: int = Field(default=0, description="Exit code that means success.")


def summary(fp: dict) -> str:
    return f"{fp['language']}{fp['language_version']}/{fp['package_manager']}/{fp.get('os') or 'linux'}"


def match_key(fp: dict) -> tuple[str, str, str]:
    return fp["language"], fp["language_version"], fp["package_manager"]
