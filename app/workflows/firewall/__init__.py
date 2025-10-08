"""Firewall workflow definition registration."""

from __future__ import annotations

from app.models import RequestType
from app.schemas import FirewallRequestCreate
from app.services import FirewallRequestService
from app.workflows import (
    StageActionDefinition,
    StageDefinition,
    WorkflowDefinition,
    registry,
)
from app.workflows.firewall import actions

FIREWALL_STAGES = [
    StageDefinition(
        id="REQUEST_RAISED",
        label="Request drafted",
        description="Firewall request drafted and pending submission to network review.",
        actions=[
            StageActionDefinition(
                id="submit",
                label="Submit for network review",
                description="Lock the draft and alert network administrators.",
                handler=actions.submit_firewall_request,
            ),
        ],
    ),
    StageDefinition(
        id="NETWORK_REVIEW",
        label="Network review",
        description="Network administrators validate scope and feasibility.",
        actions=[
            StageActionDefinition(
                id="complete_network_review",
                label="Complete review",
                description="Approve the design and move to rule collection build.",
                handler=actions.complete_network_review,
            ),
            StageActionDefinition(
                id="reject",
                label="Reject request",
                description="Reject the request with remediation guidance.",
                handler=actions.reject_firewall_request,
            ),
        ],
    ),
    StageDefinition(
        id="RULE_COLLECTION_BUILD",
        label="Rule collection build",
        description="Prepare or update Azure Firewall policy rule collections.",
        actions=[
            StageActionDefinition(
                id="prepare_rule_collection",
                label="Stage rule collection",
                description="Generate the rule collection artefacts for deployment.",
                handler=actions.prepare_rule_collection,
            ),
            StageActionDefinition(
                id="fail_stage",
                label="Mark stage failed",
                description="Record a failure during rule preparation.",
                handler=actions.mark_firewall_stage_failed,
            ),
        ],
    ),
    StageDefinition(
        id="RULE_DEPLOYMENT",
        label="Rule deployment",
        description="Deploy prepared rule collections to target environments.",
        actions=[
            StageActionDefinition(
                id="deploy_rules",
                label="Deploy firewall rules",
                description="Push changes to Azure Firewall policy via automation.",
                handler=actions.deploy_firewall_rules,
            ),
            StageActionDefinition(
                id="fail_stage",
                label="Mark stage failed",
                description="Record a deployment failure.",
                handler=actions.mark_firewall_stage_failed,
            ),
        ],
    ),
    StageDefinition(
        id="HANDOVER",
        label="Operational handover",
        description="Close the request after successful deployment and validation.",
        actions=[
            StageActionDefinition(
                id="complete_firewall_request",
                label="Complete firewall request",
                description="Document final validation and close the workflow.",
                handler=actions.complete_firewall_request,
            ),
        ],
    ),
]

registry.register(
    WorkflowDefinition(
        request_type=RequestType.FIREWALL,
        display_name="Firewall Policy",
        form_template="firewall_request_form.html",
        detail_component="request_detail.html",
        schema_class=FirewallRequestCreate,
        service_factory=FirewallRequestService,
        lifecycle=FIREWALL_STAGES,
        metadata={
            "icon": "shield",
            "description": "Request Azure Firewall rule collections and policy updates.",
        },
    )
)
