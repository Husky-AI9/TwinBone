from __future__ import annotations

from typing import Any, cast

from mangum.types import LambdaContext

from services.api.app.lambda_handler import ALLOWED_SECRET_SETTINGS, handler


def test_lambda_handler_serves_function_url_health_request() -> None:
    event: dict[str, Any] = {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/health/live",
        "rawQueryString": "",
        "headers": {"host": "example.lambda-url.us-west-2.on.aws"},
        "requestContext": {
            "accountId": "anonymous",
            "apiId": "example",
            "domainName": "example.lambda-url.us-west-2.on.aws",
            "domainPrefix": "example",
            "http": {
                "method": "GET",
                "path": "/health/live",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "pytest",
            },
            "requestId": "lambda-test-request",
            "routeKey": "$default",
            "stage": "$default",
            "time": "16/Aug/2026:00:00:00 +0000",
            "timeEpoch": 1786838400000,
        },
        "isBase64Encoded": False,
    }

    response = handler(event, cast(LambdaContext, object()))

    assert response["statusCode"] == 200
    assert '"status":"live"' in response["body"]


def test_lambda_secret_allowlist_contains_only_required_values() -> None:
    assert {
        "COCKROACH_CLUSTER_ID",
        "COCKROACH_MCP_API_KEY",
        "DATABASE_URL",
        "MCP_READONLY_DATABASE",
    } == ALLOWED_SECRET_SETTINGS
