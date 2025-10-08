"""Firewall workflow stage actions placeholders."""

from __future__ import annotations

from typing import Any


def submit_firewall_request(*, request_id: int, performed_by: str, **_: Any) -> None:
    """Submit the firewall request for network review.

    TODO: Validate prerequisite artefacts and notify the network admin queue.
    """

    raise NotImplementedError("Submit firewall request action is not implemented yet")


def complete_network_review(*, request_id: int, performed_by: str, **_: Any) -> None:
    """Complete the initial network review for the firewall request.

    TODO: Persist review outcomes, attach design notes, and advance workflow.
    """

    raise NotImplementedError("Complete network review action is not implemented yet")


def reject_firewall_request(*, request_id: int, performed_by: str, **_: Any) -> None:
    """Reject the firewall request during review.

    TODO: Notify the requester, record rejection reasons, and revert any pending
    deployment tasks.
    """

    raise NotImplementedError("Reject firewall request action is not implemented yet")


def prepare_rule_collection(*, request_id: int, performed_by: str, **_: Any) -> None:
    """Prepare or update the Azure Firewall rule collection for deployment.

    TODO: Generate policy templates, ensure idempotency, and stage GitHub pull
    requests for infrastructure-as-code changes.
    """

    raise NotImplementedError("Prepare rule collection action is not implemented yet")


def deploy_firewall_rules(*, request_id: int, performed_by: str, **_: Any) -> None:
    """Deploy firewall rules to the target environment.

    TODO: Integrate with Azure SDK/DevOps pipelines to push policy updates and
    capture deployment evidence.
    """

    raise NotImplementedError("Deploy firewall rules action is not implemented yet")


def mark_firewall_stage_failed(*, request_id: int, performed_by: str, **_: Any) -> None:
    """Mark the active firewall stage as failed pending remediation.

    TODO: Capture failure metadata, trigger incident workflows, and block
    progression until recovery steps complete.
    """

    raise NotImplementedError(
        "Mark firewall stage failed action is not implemented yet"
    )


def complete_firewall_request(*, request_id: int, performed_by: str, **_: Any) -> None:
    """Complete the firewall onboarding workflow."""

    # TODO: Confirm rule deployment, notify stakeholders, and archive artefacts.
    raise NotImplementedError("Complete firewall request action is not implemented yet")
