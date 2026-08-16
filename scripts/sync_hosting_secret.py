"""Create or update the hosted allowlisted secret without printing secret values."""

from __future__ import annotations

import argparse
import json

import boto3

from services.api.app.config import Settings

SECRET_NAME = "bonetwin/hosted/runtime"


def secret_payload(settings: Settings) -> dict[str, str]:
    values = {
        "COCKROACH_CLUSTER_ID": settings.cockroach_cluster_id,
        "COCKROACH_MCP_API_KEY": settings.reveal_cockroach_mcp_api_key(),
        "DATABASE_URL": settings.reveal_database_url(),
        "MCP_READONLY_DATABASE": settings.mcp_readonly_database,
    }
    missing = sorted(name for name, value in values.items() if not value.strip())
    if missing:
        raise RuntimeError(f"Missing hosted settings: {', '.join(missing)}")
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="bonetwin-deploy")
    parser.add_argument("--region", default="us-west-2")
    arguments = parser.parse_args()
    settings = Settings()
    payload = json.dumps(secret_payload(settings), sort_keys=True)
    client = boto3.Session(
        profile_name=arguments.profile,
        region_name=arguments.region,
    ).client("secretsmanager")
    try:
        client.describe_secret(SecretId=SECRET_NAME)
    except client.exceptions.ResourceNotFoundException:
        client.create_secret(
            Name=SECRET_NAME,
            Description="BoneTwin hosted runtime allowlisted configuration",
            SecretString=payload,
        )
        action = "created"
    else:
        client.put_secret_value(SecretId=SECRET_NAME, SecretString=payload)
        action = "updated"
    print(f"Hosted secret {action}: {SECRET_NAME} (values not displayed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
