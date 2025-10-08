"""Workflow registry exports."""

from app.workflows.base import (
    StageActionDefinition,
    StageDefinition,
    WorkflowDefinition,
    WorkflowRegistry,
    registry,
)


def _load_builtin_workflows() -> None:
    # Import modules for their side effects to register workflows.
    import app.workflows.onboarding  # noqa: F401
    import app.workflows.firewall  # noqa: F401


# Ensure built-in workflow registrations execute on import.
_load_builtin_workflows()


__all__ = [
    "StageActionDefinition",
    "StageDefinition",
    "WorkflowDefinition",
    "WorkflowRegistry",
    "registry",
]
