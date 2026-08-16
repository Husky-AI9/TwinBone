from uuid import UUID, uuid4

from pytest import raises

from services.api.app.auth import AccessScope
from services.api.app.models import UserRole


def test_access_scope_requires_nonzero_tenant_and_subject() -> None:
    with raises(ValueError, match="non-zero"):
        AccessScope(
            tenant_id=UUID(int=0),
            subject_id=uuid4(),
            role=UserRole.CLINICIAN,
        )
