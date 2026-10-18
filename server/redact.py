import re

from server.sandbox import TestRun

# Failure evidence leaves the server; raw stdout/stderr and pack files never do.
# stderr is only ever reduced to one of these fixed class names.
ERROR_CLASSES = [
    (re.compile(r"ResolutionImpossible|conflicting dependencies"), "ResolutionImpossible"),
    (re.compile(r"No matching distribution found|Could not find a version that satisfies"), "NoMatchingDistribution"),
    (re.compile(r"ModuleNotFoundError|No module named"), "ModuleNotFoundError"),
    (re.compile(r"ImportError"), "ImportError"),
    (re.compile(r"externally-managed-environment"), "ExternallyManagedEnvironment"),
    (re.compile(r"Permission denied|Read-only file system"), "PermissionDenied"),
    (re.compile(r"Temporary failure in name resolution|Network is unreachable|NewConnectionError"), "NetworkUnavailable"),
    (re.compile(r"SyntaxError"), "SyntaxError"),
    (re.compile(r"AttributeError"), "AttributeError"),
    (re.compile(r"NotImplementedError"), "NotImplementedError"),
    (re.compile(r"TypeError"), "TypeError"),
    (re.compile(r"ValueError"), "ValueError"),
    (re.compile(r"AssertionError"), "AssertionError"),
    (re.compile(r"FAILED \((failures|errors)="), "TestsFailed"),
]


def error_class(run: TestRun) -> str:
    if run.timed_out:
        return "Timeout"
    if run.exit_code == 127:
        return "CommandNotFound"
    if run.exit_code == 137:
        return "KilledOrOutOfMemory"
    for pattern, name in ERROR_CLASSES:
        if pattern.search(run.stderr) or pattern.search(run.stdout):
            return name
    return "UnknownError"


def evidence(fixture: str, run: TestRun) -> dict:
    return {
        "fixture": fixture,
        "failed_test": run.cmd,
        "exit_code": None if run.timed_out else run.exit_code,
        "error_class": error_class(run),
    }
