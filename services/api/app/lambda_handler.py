"""AWS Lambda Function URL adapter for the BoneTwin FastAPI application."""

from __future__ import annotations

import json
import os
from typing import Any

import boto3
import certifi
from mangum import Mangum

HOSTING_SECRET_ENV = "BONETWIN_HOSTING_SECRET_ID"
ALLOWED_SECRET_SETTINGS = frozenset(
    {
        "COCKROACH_CLUSTER_ID",
        "COCKROACH_MCP_API_KEY",
        "DATABASE_URL",
        "MCP_READONLY_DATABASE",
    }
)


def load_hosting_secrets() -> None:
    """Load only allowlisted application secrets before importing the app graph."""
    secret_id = os.getenv(HOSTING_SECRET_ENV, "").strip()
    if not secret_id:
        return
    response = boto3.client("secretsmanager").get_secret_value(SecretId=secret_id)
    secret_string = response.get("SecretString")
    if not isinstance(secret_string, str):
        raise RuntimeError("BoneTwin hosting secret must contain a JSON SecretString")
    payload: Any = json.loads(secret_string)
    if not isinstance(payload, dict):
        raise RuntimeError("BoneTwin hosting secret must be a JSON object")
    for name in ALLOWED_SECRET_SETTINGS:
        value = payload.get(name)
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"BoneTwin hosting secret is missing {name}")
        os.environ[name] = value


load_hosting_secrets()
os.environ.setdefault("PGSSLROOTCERT", certifi.where())

from services.api.app.main import app  # noqa: E402

handler = Mangum(app, lifespan="off")
