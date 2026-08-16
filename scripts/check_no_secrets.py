"""Fail when repository files contain common committed-secret signatures."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {
    ".cockroach-data",
    ".git",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".tools",
    ".venv",
    "build",
    "cdk.out",
    "dist",
    "node_modules",
    "out",
}
EXCLUDED_NAMES = {
    "check_no_secrets.py",
    "pnpm-lock.yaml",
    "uv.lock",
}
PATTERNS = {
    "private key": re.compile(r"-----BEGIN(?: [A-Z]+)? PRIVATE KEY-----"),
    "AWS access key": re.compile(r"(?<![A-Z0-9])A[K]IA[A-Z0-9]{16}(?![A-Z0-9])"),
    "GitHub token": re.compile(r"(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{36,}"),
    "Slack token": re.compile(r"(?<![A-Za-z0-9])xox[baprs]-[A-Za-z0-9-]{10,}"),
}


def candidate_files() -> list[Path]:
    """Return readable repository files while excluding generated dependency trees."""
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.name in EXCLUDED_NAMES or any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        files.append(path)
    return files


def main() -> int:
    """Scan text files and report signatures without printing secret values."""
    findings: list[tuple[Path, str]] = []
    for path in candidate_files():
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(content):
                findings.append((path.relative_to(ROOT), label))

    if findings:
        for path, label in findings:
            print(f"{path}: possible {label}", file=sys.stderr)
        return 1

    print("Secret signature scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
