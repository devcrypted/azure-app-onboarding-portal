"""Onboarding workflow definition registration."""

from __future__ import annotations

from app.models import RequestType
from app.schemas import OnboardingRequest
from app.services import ApplicationService
from app.workflows import (
    StageActionDefinition,
    StageDefinition,
    WorkflowDefinition,
    registry,
)
from app.workflows.onboarding import actions

ONBOARDING_STAGES = [
    StageDefinition(
        id="REQUEST_RAISED",
        label="Request raised",
        description="Initial submission recorded and routed to the onboarding queue.",
        actions=[
            StageActionDefinition(
                id="submit",
                label="Submit for approval",
                description="Lock the draft and notify approvers for review.",
                handler=actions.submit_onboarding_request,
            ),
        ],
    ),
    StageDefinition(
        id="PENDING_APPROVAL",
        label="Approval review",
        description="Admin review in progress for eligibility and completeness.",
        actions=[
            StageActionDefinition(
                id="approve",
                label="Approve onboarding",
                description="Advance the request to provisioning once approved.",
                handler=actions.review_onboarding_request,
            ),
            StageActionDefinition(
                id="reject",
                label="Reject onboarding",
                description="Reject the request and capture the rationale for auditing.",
                handler=actions.reject_onboarding_request,
            ),
        ],
    ),
    StageDefinition(
        id="APPROVED",
        label="Approved",
        description="Approval granted, onboarding preparation underway.",
        actions=[],
    ),
    StageDefinition(
        id="SUBSCRIPTION_ASSIGNMENT",
        label="Subscription assignment",
        description="Map required Azure subscriptions to each environment.",
        actions=[
            StageActionDefinition(
                id="assign_subscriptions",
                label="Assign subscriptions",
                description="Provide subscription identifiers for every environment.",
                handler=actions.assign_subscriptions,
            ),
        ],
    ),
    StageDefinition(
        id="FOUNDATION_INFRA",
        label="Foundation infra",
        description="Provision base landing zones, networking, and security.",
        actions=[
            StageActionDefinition(
                id="complete_foundation",
                label="Mark foundation complete",
                description="Confirm baseline infrastructure delivery is complete.",
                handler=actions.complete_foundation_infra,
            ),
            StageActionDefinition(
                id="fail_stage",
                label="Mark stage failed",
                description="Record a failure and trigger remediation workflows.",
                handler=actions.mark_stage_failed,
            ),
        ],
    ),
    StageDefinition(
        id="INFRASTRUCTURE",
        label="Application infra",
        description="Deploy application-specific services and integrations.",
        actions=[
            StageActionDefinition(
                id="complete_infra",
                label="Mark infrastructure complete",
                description="Confirm application infrastructure was deployed.",
                handler=actions.complete_application_infra,
            ),
            StageActionDefinition(
                id="fail_stage",
                label="Mark stage failed",
                description="Record a failure and trigger remediation workflows.",
                handler=actions.mark_stage_failed,
            ),
        ],
    ),
    StageDefinition(
        id="HANDOVER",
        label="Handover",
        description="Transfer ownership, documentation, and access to the customer team.",
        actions=[
            StageActionDefinition(
                id="complete_handover",
                label="Complete handover",
                description="Finalize acceptance and close out the onboarding request.",
                handler=actions.complete_handover,
            ),
        ],
    ),
]

registry.register(
    WorkflowDefinition(
        request_type=RequestType.ONBOARDING,
        display_name="Application Onboarding",
        form_template="request_form.html",
        detail_component="request_detail.html",
        schema_class=OnboardingRequest,
        service_factory=ApplicationService,
        lifecycle=ONBOARDING_STAGES,
        metadata={
            "icon": "clipboard-check",
            "description": "Provision Azure resources and subscriptions for a new application.",
        },
    )
)
