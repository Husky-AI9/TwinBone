"""Load deterministic, synthetic-only Phase 1 seed records."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Connection

from services.agent.bonetwin_agent.bedrock import BedrockRuntime
from services.agent.bonetwin_agent.trust import deterministic_embedding
from services.api.app.config import get_settings
from services.api.app.db import create_database_engine
from services.api.app.services.synthetic_seed import seed_synthetic_workflow

SEED_FILE = Path(__file__).resolve().parents[1] / "database" / "seed" / "phase1.sql"


def execute_sql_file(connection: Connection, path: Path) -> None:
    for statement in path.read_text(encoding="utf-8").split(";\n"):
        if stripped := statement.strip():
            connection.exec_driver_sql(stripped)


def main() -> int:
    settings = get_settings()
    engine = create_database_engine(settings)
    runtime: BedrockRuntime | None = None
    if settings.bedrock_mode == "live":
        runtime = BedrockRuntime.from_aws(
            region=settings.aws_region,
            profile=settings.aws_profile,
            chat_model_id=settings.bedrock_chat_model_id,
            embedding_model_id=settings.bedrock_embedding_model_id,
            guardrail_id=settings.bedrock_guardrail_id,
            guardrail_version=settings.bedrock_guardrail_version,
            timeout_seconds=settings.bedrock_timeout_seconds,
        )
    try:
        with engine.begin() as connection:
            execute_sql_file(connection, SEED_FILE)
            seed_synthetic_workflow(
                connection,
                embed=runtime.embed if runtime is not None else deterministic_embedding,
                embedding_model=(
                    runtime.embedding_model_id
                    if runtime is not None
                    else "bonetwin-deterministic-local-v1"
                ),
            )
    finally:
        engine.dispose()
    print("Seeded the synthetic tenant, demo roles, subject, structured timeline, and memory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
