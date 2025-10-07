"""Repository for firewall request persistence and duplicate detection."""

from __future__ import annotations

from typing import List, Sequence, Tuple

from flask_sqlalchemy import SQLAlchemy

from app.models import Application, FirewallRequest, FirewallRuleEntry, RequestStatus
from app.repositories.base_repository import BaseRepository


class FirewallRequestRepository(BaseRepository[FirewallRequest]):
    """Data access layer for firewall requests and rule entries."""

    def __init__(self, db: SQLAlchemy) -> None:
        super().__init__(db, FirewallRequest)

    def add(self, request: FirewallRequest) -> FirewallRequest:
        """Persist a firewall request and return it."""
        self.db.session.add(request)
        return request

    def find_duplicates(
        self, duplicate_keys: Sequence[str]
    ) -> List[Tuple[FirewallRuleEntry, FirewallRequest, Application]]:
        """Return rule entries that already exist for the supplied duplicate keys."""
        if not duplicate_keys:
            return []

        rows = (
            self.db.session.query(FirewallRuleEntry, FirewallRequest, Application)
            .join(
                FirewallRequest,
                FirewallRuleEntry.firewall_request_id == FirewallRequest.id,
            )
            .join(Application, FirewallRequest.app_id == Application.id)
            .filter(FirewallRuleEntry.duplicate_key.in_(duplicate_keys))
            .filter(
                ~Application.status.in_(
                    [
                        RequestStatus.REJECTED,
                        RequestStatus.CANCELLED,
                        RequestStatus.FAILED,
                    ]
                )
            )
            .all()
        )

        return [(entry, request, application) for entry, request, application in rows]

    def list_for_user(self, user_email: str) -> List[FirewallRequest]:
        """List firewall requests initiated by a specific user."""
        return (
            self.query()
            .join(Application, FirewallRequest.app_id == Application.id)
            .filter(Application.requested_by == user_email)
            .order_by(FirewallRequest.created_at.desc())
            .all()
        )

    def list_all(self) -> List[FirewallRequest]:
        """List all firewall requests ordered by creation date."""
        return self.query().order_by(FirewallRequest.created_at.desc()).all()
