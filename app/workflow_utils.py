"""Workflow utility functions for request lifecycle management."""

from datetime import datetime, timedelta
from typing import Optional

from flask import current_app


def get_workflow_config() -> dict:
    """Get workflow configuration from app config.

    Returns:
        Dictionary with workflow configuration
    """
    return current_app.config.get("WORKFLOW_CONFIG", {})


def calculate_business_days_between(
    start_date: datetime, end_date: Optional[datetime] = None
) -> int:
    """Calculate number of business days between two dates.

    Args:
        start_date: Start date
        end_date: End date (defaults to now)

    Returns:
        Number of business days
    """
    if end_date is None:
        end_date = datetime.utcnow()

    config = get_workflow_config()
    business_days_only = config.get("BUSINESS_DAYS_ONLY", True)

    if not business_days_only:
        # If not using business days, return calendar days
        return (end_date - start_date).days

    # Count business days (exclude weekends)
    current_date = start_date.date()
    end = end_date.date()
    business_days = 0

    while current_date < end:
        # Monday = 0, Sunday = 6
        if current_date.weekday() < 5:  # Monday to Friday
            business_days += 1
        current_date += timedelta(days=1)

    return business_days


def can_expedite(application) -> tuple[bool, Optional[str]]:
    """Check if a request can be expedited.

    Args:
        application: Application instance

    Returns:
        Tuple of (can_expedite: bool, reason: str or None)
    """
    config = get_workflow_config()

    # Check if status allows expedite
    expeditable_statuses = config.get("EXPEDITABLE_STATUSES", ["PENDING"])
    if application.status.value not in expeditable_statuses:
        return False, f"Cannot expedite request with status {application.status.value}"

    # Check if already expedited
    if application.expedite_requested:
        return False, "Expedite has already been requested"

    # Check if enough time has passed
    threshold_days = config.get("EXPEDITE_THRESHOLD_DAYS", 2)

    # Use created_at for draft->pending, or updated_at for status changes
    reference_date = application.created_at
    if application.status.value == "PENDING" and application.updated_at:
        # If status was changed (draft->pending), use updated_at
        reference_date = application.updated_at

    days_passed = calculate_business_days_between(reference_date)

    if days_passed < threshold_days:
        return (
            False,
            f"Cannot expedite before {threshold_days} business days have passed",
        )

    return True, None


def can_cancel(application) -> tuple[bool, Optional[str]]:
    """Check if a request can be cancelled.

    Args:
        application: Application instance

    Returns:
        Tuple of (can_cancel: bool, reason: str or None)
    """
    config = get_workflow_config()

    # Check if status allows cancellation
    cancellable_statuses = config.get("CANCELLABLE_STATUSES", ["DRAFT", "PENDING"])
    if application.status.value not in cancellable_statuses:
        return False, f"Cannot cancel request with status {application.status.value}"

    return True, None


def can_edit(application) -> tuple[bool, Optional[str]]:
    """Check if a request can be edited.

    Args:
        application: Application instance

    Returns:
        Tuple of (can_edit: bool, reason: str or None)
    """
    config = get_workflow_config()

    # Check if status allows editing
    editable_statuses = config.get("EDITABLE_STATUSES", ["DRAFT"])
    if application.status.value not in editable_statuses:
        return False, f"Cannot edit request with status {application.status.value}"

    if not application.is_editable:
        return False, "Request is not editable"

    return True, None


def can_comment(application) -> tuple[bool, Optional[str]]:
    """Check if comments can be added to a request.

    Args:
        application: Application instance

    Returns:
        Tuple of (can_comment: bool, reason: str or None)
    """
    config = get_workflow_config()

    # Check if status allows comments
    commentable_statuses = config.get(
        "COMMENTABLE_STATUSES",
        [
            "DRAFT",
            "PENDING",
            "APPROVED",
            "SUBSCRIPTION_ASSIGNED",
            "FOUNDATION_INFRA",
            "INFRASTRUCTURE",
            "HANDOVER",
        ],
    )

    if application.status.value not in commentable_statuses:
        return (
            False,
            f"Cannot comment on request with status {application.status.value}",
        )

    return True, None


def get_status_display_name(status_value: str) -> str:
    """Get user-friendly display name for a status.

    Args:
        status_value: Status enum value

    Returns:
        Display name
    """
    config = get_workflow_config()
    display_names = config.get("STATUS_DISPLAY_NAMES", {})
    return display_names.get(status_value, status_value.replace("_", " ").title())


def get_stage_display_name(stage_value: str) -> str:
    """Get user-friendly display name for a workflow stage.

    Args:
        stage_value: Stage enum value

    Returns:
        Display name
    """
    config = get_workflow_config()
    display_names = config.get("STAGE_DISPLAY_NAMES", {})
    return display_names.get(stage_value, stage_value.replace("_", " ").title())
