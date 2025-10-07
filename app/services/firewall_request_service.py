"""Service layer for firewall request workflow."""

from __future__ import annotations

import hashlib
import json
from typing import List, Optional, Sequence

from flask_sqlalchemy import SQLAlchemy

from app.models import FirewallRequest, FirewallRuleEntry, RequestType, WorkflowStage
from app.repositories import (
    AuditRepository,
    FirewallRequestRepository,
    TimelineRepository,
)
from app.services.application_service import ApplicationService
from app.schemas import FirewallRequestCreate, FirewallRuleEntryInput


class DuplicateFirewallRuleError(Exception):
    """Raised when submitted firewall rules already exist."""

    def __init__(self, duplicates: List[dict]):
        super().__init__("Duplicate firewall rules detected")
        self.duplicates = duplicates


class FirewallRequestService:
    """Business logic for firewall request submissions."""

    def __init__(self, db: SQLAlchemy) -> None:
        self.db = db
        self.application_service = ApplicationService(db)
        self.firewall_repo = FirewallRequestRepository(db)
        self.audit_repo = AuditRepository(db)
        self.timeline_repo = TimelineRepository(db)

    def list_requests(
        self, user_email: str, *, include_all: bool = False
    ) -> List[FirewallRequest]:
        """List firewall requests available to the caller."""
        if include_all:
            return self.firewall_repo.list_all()
        return self.firewall_repo.list_for_user(user_email)

    def create_firewall_request(
        self,
        payload: FirewallRequestCreate,
        *,
        requested_by: str,
        ip_address: Optional[str] = None,
    ) -> FirewallRequest:
        """Create a firewall request along with its rule entries."""

        duplicate_keys = [
            self._build_duplicate_key(rule) for rule in payload.rule_entries
        ]
        duplicates = self.firewall_repo.find_duplicates(duplicate_keys)

        if duplicates:
            duplicate_payload = [
                {
                    "rule": entry.to_dict(),
                    "existing_request": request.to_dict(),
                    "application": {
                        "id": request.application.id,
                        "app_code": request.application.app_code,
                        "status": request.application.status.value,
                    },
                }
                for entry, request, _ in duplicates
            ]
            raise DuplicateFirewallRuleError(duplicate_payload)

        app_payload = {
            "request_type": RequestType.FIREWALL,
            "application_name": payload.application_name,
            "organization": payload.organization,
            "lob": payload.lob,
            "platform": payload.platform,
            "save_as_draft": False,
        }

        application = self.application_service.create_application(
            data=app_payload,
            requested_by=requested_by,
            ip_address=ip_address,
        )

        firewall_request = FirewallRequest(
            app_id=application.id,
            environment_scopes=json.dumps(payload.environment_scopes),
            destination_service=payload.destination_service,
            justification=payload.justification,
            requested_effective_date=payload.requested_effective_date,
            expires_at=payload.expires_at,
            github_pr_url=payload.github_pr_url,
            duplicate_hash=self._build_request_hash(duplicate_keys),
            application_name_at_submission=application.application_name,
            organization_at_submission=application.organization,
            lob_at_submission=application.lob,
            requester_email_at_submission=application.requested_by,
        )

        for rule, duplicate_key in zip(payload.rule_entries, duplicate_keys):
            normalized_ports = self._normalise_ports(rule.ports)
            entry = FirewallRuleEntry(
                source=rule.source,
                destination=rule.destination,
                ports="|".join(normalized_ports),
                protocol=rule.protocol,
                direction=rule.direction,
                description=rule.description,
                duplicate_key=duplicate_key,
            )
            firewall_request.rule_entries.append(entry)

        self.firewall_repo.add(firewall_request)

        self.audit_repo.create(
            request_type="CREATE",
            app_id=application.id,
            user_email=requested_by,
            action=f"Created firewall request {application.app_code}",
            details=f"Submitted {len(payload.rule_entries)} firewall rule(s)",
            ip_address=ip_address,
        )

        self.timeline_repo.create(
            stage=WorkflowStage.PENDING_APPROVAL,
            status="IN_PROGRESS",
            message="Firewall request awaiting network admin review",
            performed_by=requested_by,
            app_id=application.id,
        )

        self.firewall_repo.commit()

        return firewall_request

    @staticmethod
    def _normalise_ports(ports: Sequence[str]) -> List[str]:
        normalised: List[str] = []
        for port in ports:
            parts = [
                segment.strip() for segment in str(port).split(",") if segment.strip()
            ]
            normalised.extend(parts)
        return sorted({p for p in normalised})

    @staticmethod
    def _build_duplicate_key(rule: FirewallRuleEntryInput) -> str:
        key_components = [
            rule.source.lower(),
            rule.destination.lower(),
            "|".join(FirewallRequestService._normalise_ports(rule.ports)),
            rule.protocol.upper(),
            rule.direction.upper(),
        ]
        dedupe_string = "::".join(key_components)
        return hashlib.sha256(dedupe_string.encode("utf-8")).hexdigest()

    @staticmethod
    def _build_request_hash(duplicate_keys: Sequence[str]) -> Optional[str]:
        if not duplicate_keys:
            return None
        combined = "::".join(sorted(duplicate_keys))
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()
