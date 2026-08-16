"""Application workflow-store selection."""

from services.api.app.config import get_settings
from services.api.app.services.cockroach_store import CockroachWorkflowStore
from services.api.app.services.demo_store import DemoStore, demo_store
from services.api.app.services.workflow_store import WorkflowStore


def create_workflow_store() -> WorkflowStore:
    """Use CockroachDB unless unit tests explicitly request the memory double."""
    settings = get_settings()
    if settings.workflow_store_mode == "memory":
        return demo_store
    return CockroachWorkflowStore(settings=settings)


workflow_store = create_workflow_store()

__all__ = [
    "CockroachWorkflowStore",
    "DemoStore",
    "WorkflowStore",
    "create_workflow_store",
    "demo_store",
    "workflow_store",
]
