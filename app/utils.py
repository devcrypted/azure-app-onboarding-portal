"""Utility functions for TradeX Platform Onboarding."""

from typing import Optional
from app.models import Application, RequestType, db


def generate_app_code(request_type: RequestType) -> str:
    """
    Generate a unique app code based on request type.

    Format: <PREFIX>-<5-digit-number>
    - ONBOARDING: APP-00001
    - FIREWALL: FW-00001
    - ORGANIZATION: ORG-00001
    - LOB: LOB-00001
    - SUBSCRIPTION: SUB-00001

    Args:
        request_type: The type of request (RequestType enum)

    Returns:
        str: Generated app code (e.g., "APP-00001")
    """
    # Define prefixes for each request type
    prefix_map = {
        RequestType.ONBOARDING: "APP",
        RequestType.FIREWALL: "FW",
        RequestType.ORGANIZATION: "ORG",
        RequestType.LOB: "LOB",
        RequestType.SUBSCRIPTION: "SUB",
    }

    prefix = prefix_map.get(request_type, "REQ")

    # Get the latest app code for this request type
    # Query for codes starting with this prefix
    latest_app = (
        db.session.query(Application)
        .filter(Application.request_type == request_type)
        .filter(Application.app_code.like(f"{prefix}-%"))
        .order_by(Application.id.desc())
        .first()
    )

    if latest_app and latest_app.app_code:
        # Extract the number from the latest code (e.g., "APP-00001" -> 1)
        try:
            last_number = int(latest_app.app_code.split("-")[1])
            next_number = last_number + 1
        except (IndexError, ValueError):
            # If parsing fails, start from 1
            next_number = 1
    else:
        # No existing codes for this type, start from 1
        next_number = 1

    # Format with 5 digits
    return f"{prefix}-{next_number:05d}"


def validate_app_slug_uniqueness(app_slug: Optional[str]) -> bool:
    """
    Check if an app slug is unique across all applications.

    Args:
        app_slug: The app slug to validate

    Returns:
        bool: True if unique (or None), False if already exists
    """
    if not app_slug:
        return True

    # Convert to lowercase to match validation rules
    existing = (
        db.session.query(Application).filter_by(app_slug=app_slug.lower()).first()
    )
    return existing is None


def validate_subscription_id_uniqueness(subscription_id: str) -> bool:
    """
    Check if a subscription ID is unique in subscription management.

    Args:
        subscription_id: The Azure subscription GUID to validate

    Returns:
        bool: True if unique, False if already exists
    """
    from app.models import SubscriptionManagement

    existing = (
        db.session.query(SubscriptionManagement)
        .filter_by(subscription_id=subscription_id)
        .first()
    )
    return existing is None
