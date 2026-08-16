"""Authorization primitives."""

from services.api.app.auth.principal import (
    DEMO_SUBJECT_ID,
    DEMO_TENANT_ID,
    Principal,
    get_current_principal,
    require_role,
    require_subject,
)
from services.api.app.auth.scope import AccessScope

__all__ = [
    "DEMO_SUBJECT_ID",
    "DEMO_TENANT_ID",
    "AccessScope",
    "Principal",
    "get_current_principal",
    "require_role",
    "require_subject",
]
