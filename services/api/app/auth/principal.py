"""Authenticated principal construction for Cognito and deterministic local demo mode."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Header, HTTPException, status
from jwt import PyJWKClient

from services.api.app.config import Settings, get_settings
from services.api.app.models import UserRole

DEMO_TENANT_ID = UUID("10000000-0000-4000-8000-000000000001")
DEMO_SUBJECT_ID = UUID("30000000-0000-4000-8000-000000000001")
AUTH_SETTINGS = get_settings()


@dataclass(frozen=True, slots=True)
class Principal:
    """Trusted identity derived at the API boundary."""

    user_id: UUID
    tenant_id: UUID
    role: UserRole
    display_name: str
    cognito_subject: str
    allowed_subject_ids: frozenset[UUID]


DEMO_PRINCIPALS: dict[str, Principal] = {
    "demo-clinician": Principal(
        user_id=UUID("20000000-0000-4000-8000-000000000002"),
        tenant_id=DEMO_TENANT_ID,
        role=UserRole.CLINICIAN,
        display_name="Dr. Sam Rivera",
        cognito_subject="demo-clinician",
        allowed_subject_ids=frozenset({DEMO_SUBJECT_ID}),
    ),
    "demo-judge": Principal(
        user_id=UUID("20000000-0000-4000-8000-000000000001"),
        tenant_id=DEMO_TENANT_ID,
        role=UserRole.JUDGE,
        display_name="Demo Judge",
        cognito_subject="demo-judge",
        allowed_subject_ids=frozenset({DEMO_SUBJECT_ID}),
    ),
    "demo-patient": Principal(
        user_id=UUID("20000000-0000-4000-8000-000000000003"),
        tenant_id=DEMO_TENANT_ID,
        role=UserRole.PATIENT,
        display_name="Synthetic Patient",
        cognito_subject="demo-patient",
        allowed_subject_ids=frozenset({DEMO_SUBJECT_ID}),
    ),
}


def _unauthorized(message: str = "Authentication required") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _decode_cognito_token(token: str, settings: Settings) -> Principal:
    """Verify Cognito JWT signature, issuer, audience, and authorization claims."""
    if not settings.cognito_client_id or not settings.cognito_user_pool_id:
        raise _unauthorized("Cognito is not configured")
    issuer = (
        f"https://cognito-idp.{settings.aws_region}.amazonaws.com/{settings.cognito_user_pool_id}"
    )
    try:
        signing_key = PyJWKClient(f"{issuer}/.well-known/jwks.json").get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            audience=settings.cognito_client_id,
            algorithms=["RS256"],
            issuer=issuer,
        )
    except jwt.PyJWTError as error:
        raise _unauthorized("Invalid access token") from error
    if claims.get("token_use") not in {"id", "access"}:
        raise _unauthorized("Unsupported Cognito token type")
    role_name = str(claims.get("custom:role", ""))
    try:
        role = UserRole(role_name)
        user_id = UUID(str(claims["custom:user_id"]))
        tenant_id = UUID(str(claims["custom:tenant_id"]))
        subject_ids = frozenset(
            UUID(value) for value in str(claims.get("custom:subject_ids", "")).split(",") if value
        )
    except (KeyError, ValueError) as error:
        raise _unauthorized("Token is missing required authorization claims") from error
    return Principal(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        display_name=str(claims.get("name", "BoneTwin user")),
        cognito_subject=str(claims.get("sub", "")),
        allowed_subject_ids=subject_ids,
    )


def authenticate_token(token: str, settings: Settings) -> Principal:
    """Resolve a demo bearer token or a production identity boundary."""
    if settings.auth_mode == "mock":
        principal = DEMO_PRINCIPALS.get(token)
        if principal is None:
            raise _unauthorized("Invalid demo token")
        return principal
    return _decode_cognito_token(token, settings)


def get_current_principal(
    authorization: str | None = Header(default=None),
) -> Principal:
    """FastAPI dependency that rejects missing and malformed bearer tokens."""
    if authorization is None or not authorization.startswith("Bearer "):
        raise _unauthorized()
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise _unauthorized()
    return authenticate_token(token, AUTH_SETTINGS)


def require_subject(principal: Principal, subject_id: UUID) -> None:
    """Hide unauthorized subject existence behind a scoped 404 response."""
    if subject_id not in principal.allowed_subject_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")


def require_role(principal: Principal, *roles: UserRole) -> None:
    """Enforce a role allowlist for sensitive actions."""
    if principal.role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
