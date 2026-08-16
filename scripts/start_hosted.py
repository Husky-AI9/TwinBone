"""Prepare the synthetic CockroachDB schema and start the hosted API."""

from __future__ import annotations

import os

import uvicorn


def _enabled(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    """Apply durable schema state before importing and serving the API app."""
    if os.getenv("APP_ENV") != "hosted":
        raise RuntimeError("scripts.start_hosted is restricted to APP_ENV=hosted")

    from scripts.migrate import main as migrate

    migrate()
    if _enabled("SEED_ON_STARTUP", default=True):
        from scripts.seed import main as seed

        seed()

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "services.api.app.main:app",
        host="0.0.0.0",
        port=port,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
