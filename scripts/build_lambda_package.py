"""Build a deterministic Linux/x86_64 Lambda ZIP without requiring Docker."""

from __future__ import annotations

import compileall
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist" / "lambda"
PACKAGE = DIST / "package"
ARCHIVE = DIST / "bonetwin-api.zip"
UV_COMMAND = (
    ("py", "-3.11", "-m", "uv")
    if os.name == "nt"
    else (os.environ.get("BONETWIN_UV_COMMAND", "uv"),)
)


def run(*arguments: str) -> None:
    subprocess.run(arguments, cwd=ROOT, check=True)  # noqa: S603


def copy_python_tree(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(
            "__pycache__",
            "*.pyc",
            "tests",
            ".pytest_cache",
        ),
    )


def main() -> int:
    shutil.rmtree(DIST, ignore_errors=True)
    PACKAGE.mkdir(parents=True)
    requirements = DIST / "requirements.txt"
    run(
        *UV_COMMAND,
        "export",
        "--frozen",
        "--no-dev",
        "--no-emit-project",
        "--format",
        "requirements-txt",
        "--output-file",
        str(requirements),
    )
    run(
        *UV_COMMAND,
        "pip",
        "install",
        "--python-platform",
        "x86_64-manylinux_2_17",
        "--python-version",
        "3.12",
        "--target",
        str(PACKAGE),
        "--requirements",
        str(requirements),
    )
    copy_python_tree(ROOT / "services", PACKAGE / "services")
    shutil.copytree(ROOT / "output" / "pdf", PACKAGE / "output" / "pdf")
    compileall.compile_dir(PACKAGE, quiet=1, force=True)
    for cache in PACKAGE.rglob("__pycache__"):
        shutil.rmtree(cache)
    for metadata in PACKAGE.glob("*.dist-info"):
        for filename in ("RECORD", "INSTALLER", "REQUESTED"):
            (metadata / filename).unlink(missing_ok=True)
    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in sorted(PACKAGE.rglob("*")):
            if path.is_file():
                bundle.write(path, path.relative_to(PACKAGE).as_posix())
    uncompressed_size = sum(path.stat().st_size for path in PACKAGE.rglob("*") if path.is_file())
    if uncompressed_size > 250 * 1024 * 1024:
        raise RuntimeError("Lambda package exceeds the 250 MiB uncompressed limit")
    print(
        f"Lambda package ready: {ARCHIVE} "
        f"({ARCHIVE.stat().st_size / 1024 / 1024:.1f} MiB compressed, "
        f"{uncompressed_size / 1024 / 1024:.1f} MiB uncompressed)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
