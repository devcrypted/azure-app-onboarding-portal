"""Onboarding workflow stage actions.

Each action handler will encapsulate the business logic that should execute when
an operator performs the associated transition. Implementations intentionally
raise ``NotImplementedError`` for now to signal future work.
"""

from __future__ import annotations

from typing import Any


def submit_onboarding_request(*, request_id: int, performed_by: str, **_: Any) -> None:
    """Submit a draft onboarding request for approval.

    TODO: Integrate validation, notify approvers, and trigger workflow events
    once the orchestration service is connected.
    """

    raise NotImplementedError("Submit onboarding request action is not implemented yet")


def review_onboarding_request(*, request_id: int, performed_by: str, **_: Any) -> None:
    """Complete the approval review for an onboarding request.

    TODO: Implement approval decision capture, timeline updates, and downstream
    provisioning triggers.
    """

    raise NotImplementedError("Review onboarding request action is not implemented yet")


def reject_onboarding_request(*, request_id: int, performed_by: str, **_: Any) -> None:
    """Reject an onboarding request during the review stage.

    TODO: Persist rejection reasons, notify requesters, and mark dependent
    tasks as cancelled.
    """

    raise NotImplementedError("Reject onboarding request action is not implemented yet")


def assign_subscriptions(*, request_id: int, performed_by: str, **_: Any) -> None:
    """Assign Azure subscriptions to onboarding environments.

    TODO: Wire up subscription catalog lookups, validation, and persistence.
    """

    raise NotImplementedError("Assign subscriptions action is not implemented yet")


def complete_foundation_infra(*, request_id: int, performed_by: str, **_: Any) -> None:
    """Mark foundation infrastructure as delivered.

    TODO: Enforce dependency checks and capture deployment evidence prior to
    marking the stage as complete.
    """

    raise NotImplementedError("Complete foundation infra action is not implemented yet")


def complete_application_infra(*, request_id: int, performed_by: str, **_: Any) -> None:
    """Mark application infrastructure delivery as complete.

    TODO: Capture deployment metadata and notify stakeholders before advancing
    to handover.
    """

    raise NotImplementedError(
        "Complete application infra action is not implemented yet"
    )


def complete_handover(*, request_id: int, performed_by: str, **_: Any) -> None:
    """Complete the onboarding handover stage.

    TODO: Attach final artefacts, confirm acceptance, and close out the request.
    """

    raise NotImplementedError("Complete handover action is not implemented yet")


def mark_stage_failed(*, request_id: int, performed_by: str, **_: Any) -> None:
    """Mark the active onboarding stage as failed.

    TODO: Capture failure metadata, trigger escalation policies, and block
    further progress until remediation is complete.
    """

    raise NotImplementedError("Mark stage failed action is not implemented yet")
