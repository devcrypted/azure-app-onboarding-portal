"""Workflow definition models for request orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Protocol

from app.models import RequestType


class StageActionHandler(Protocol):
    """Protocol describing a stage action callable."""

    def __call__(
        self, *, request_id: int, performed_by: str, **kwargs: Any
    ) -> None: ...


@dataclass(frozen=True)
class StageActionDefinition:
    """Metadata describing an action that can be executed within a stage."""

    id: str
    label: str
    description: str
    handler: StageActionHandler


@dataclass(frozen=True)
class StageDefinition:
    """Metadata describing the lifecycle stage of a workflow."""

    id: str
    label: str
    description: str
    actions: List[StageActionDefinition] = field(default_factory=list)


@dataclass(frozen=True)
class WorkflowDefinition:
    """Container for request workflow configuration."""

    request_type: RequestType
    display_name: str
    form_template: str
    detail_component: str
    schema_class: Any
    service_factory: Callable[[Any], Any]
    lifecycle: List[StageDefinition]
    metadata: Dict[str, Any] = field(default_factory=dict)


class UnknownWorkflowError(KeyError):
    """Raised when a workflow definition is not registered."""


class WorkflowRegistry:
    """Registry storing workflow definitions keyed by RequestType."""

    def __init__(self) -> None:
        self._definitions: Dict[RequestType, WorkflowDefinition] = {}

    def register(self, definition: WorkflowDefinition) -> None:
        if definition.request_type in self._definitions:
            raise ValueError(
                f"Workflow for {definition.request_type.value} already registered"
            )
        self._definitions[definition.request_type] = definition

    def get(self, request_type: RequestType) -> WorkflowDefinition:
        try:
            return self._definitions[request_type]
        except KeyError as exc:
            raise UnknownWorkflowError(request_type.value) from exc

    def all(self) -> List[WorkflowDefinition]:
        return list(self._definitions.values())


registry = WorkflowRegistry()
"""Global workflow registry instance."""
