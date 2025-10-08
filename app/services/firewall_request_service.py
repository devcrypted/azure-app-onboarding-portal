"""Service layer for firewall request workflow."""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Optional, Sequence, Tuple, Union, cast

from flask_sqlalchemy import SQLAlchemy

from app.models import (
    FirewallRequest,
    FirewallRuleCollection,
    FirewallRuleEntry,
    RequestType,
    WorkflowStage,
)
from app.repositories import (
    AuditRepository,
    FirewallRequestRepository,
    TimelineRepository,
)
from app.services.application_service import ApplicationService
from app.schemas import (
    ApplicationRuleGroupInput,
    ApplicationRuleInput,
    FirewallRequestCreate,
    NatRuleGroupInput,
    NatRuleInput,
    NetworkRuleGroupInput,
    NetworkRuleInput,
)


class DuplicateFirewallRuleError(Exception):
    """Raised when submitted firewall rules already exist."""

    def __init__(self, duplicates: List[dict]):
        super().__init__("Duplicate firewall rules detected")
        self.duplicates = duplicates


class FirewallRequestService:
    """Business logic for firewall request submissions."""

    PRIORITY_BASELINE = {
        "APPLICATION": 400,
        "NETWORK": 6500,
        "NAT": 100,
    }
    PRIORITY_INCREMENT = 100

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

        rule_groups = self._iter_groups(payload)
        duplicate_keys = [
            self._build_duplicate_key(collection_type, rule)
            for collection_type, group in rule_groups
            for rule in group.rules
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

        # Resolve application ID (supports numeric ID, app_code, or app_slug)
        source_application = None
        app_id_str = str(payload.source_application_id)

        if app_id_str.isdigit():
            source_application = self.application_service.get_application(
                int(app_id_str)
            )

        if not source_application:
            # Try to find by app_code or app_slug
            from app.models import Application

            source_application = (
                self.db.session.query(Application)
                .filter(
                    (Application.app_code == app_id_str)
                    | (Application.app_slug == app_id_str)
                )
                .first()
            )

        if not source_application:
            raise ValueError(
                f"Application '{payload.source_application_id}' not found. Please provide a valid ID, app code, or slug."
            )
        if source_application.request_type != RequestType.ONBOARDING:
            raise ValueError("Firewall requests must target an onboarding application")

        # Map abbreviated environment codes to full names
        env_code_to_name = {
            "DEV": "DEVELOPMENT",
            "TEST": "TESTING",
            "QA": "QA",
            "STAGE": "STAGING",
            "UAT": "UAT",
            "PROD": "PRODUCTION",
            "DR": "DR",
        }

        # Get available environment names from the application
        available_scopes = {
            env.environment_name.strip().upper()
            for env in source_application.environments
        }

        # Convert incoming environment scopes (which may be abbreviated) to full names
        normalized_scopes = set()
        for scope in payload.environment_scopes:
            scope_upper = scope.strip().upper()
            # Try to map abbreviated code to full name, otherwise use as-is
            full_name = env_code_to_name.get(scope_upper, scope_upper)
            normalized_scopes.add(full_name)

        invalid_scopes = normalized_scopes - available_scopes
        if invalid_scopes:
            raise ValueError(
                "Environment scopes must match the application's environments; "
                f"invalid: {', '.join(sorted(invalid_scopes))}"
            )

        app_payload = {
            "request_type": RequestType.FIREWALL,
            "application_name": source_application.application_name,
            "organization": source_application.organization,
            "lob": source_application.lob,
            "platform": source_application.platform,
            "save_as_draft": False,
        }

        application = self.application_service.create_application(
            data=app_payload,
            requested_by=requested_by,
            ip_address=ip_address,
        )

        firewall_request = FirewallRequest(
            app_id=application.id,
            source_application_id=source_application.id,
            collection_name=payload.collection_name,
            ip_groups=json.dumps(payload.ip_groups or {}),
            environment_scopes=json.dumps(payload.environment_scopes),
            destination_service=getattr(payload, "destination_service", None),
            justification=payload.justification,
            requested_effective_date=payload.requested_effective_date,
            expires_at=payload.expires_at,
            github_pr_url=payload.github_pr_url,
            duplicate_hash=self._build_request_hash(duplicate_keys),
            application_name_at_submission=source_application.application_name,
            organization_at_submission=source_application.organization,
            lob_at_submission=source_application.lob,
            requester_email_at_submission=application.requested_by,
        )

        self.firewall_repo.add(firewall_request)

        collections_by_type: Dict[str, FirewallRuleCollection] = {}
        for collection_type, group in rule_groups:
            collection = collections_by_type.get(collection_type)
            if collection is None:
                priority = self._determine_priority(
                    source_application_id=source_application.id,
                    collection_type=collection_type,
                    requested_priority=group.priority,
                )
                collection = FirewallRuleCollection(
                    collection_type=collection_type,
                    action=group.action,
                    priority=priority,
                )
                firewall_request.rule_collections.append(collection)
                collections_by_type[collection_type] = collection

            for rule in group.rules:
                duplicate_key = self._build_duplicate_key(collection_type, rule)
                entry = self._build_rule_entry(
                    request=firewall_request,
                    collection=collection,
                    collection_type=collection_type,
                    rule=rule,
                    duplicate_key=duplicate_key,
                )
                collection.rule_entries.append(entry)

        firewall_request.collection_document = json.dumps(
            self._build_collection_document(firewall_request), indent=4
        )

        total_rules = len(duplicate_keys)

        self.audit_repo.create(
            request_type="CREATE",
            app_id=application.id,
            user_email=requested_by,
            action=f"Created firewall request {application.app_code}",
            details=f"Submitted {total_rules} firewall rule(s)",
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

    def _iter_groups(self, payload: FirewallRequestCreate) -> List[
        Tuple[
            str,
            Union[ApplicationRuleGroupInput, NetworkRuleGroupInput, NatRuleGroupInput],
        ]
    ]:
        groups: List[
            Tuple[
                str,
                Union[
                    ApplicationRuleGroupInput,
                    NetworkRuleGroupInput,
                    NatRuleGroupInput,
                ],
            ]
        ] = []

        if payload.application_rules:
            groups.append(("APPLICATION", payload.application_rules))
        if payload.network_rules:
            groups.append(("NETWORK", payload.network_rules))
        if payload.nat_rules:
            groups.append(("NAT", payload.nat_rules))
        return groups

    def _determine_priority(
        self,
        *,
        source_application_id: int,
        collection_type: str,
        requested_priority: Optional[int],
    ) -> int:
        if requested_priority is not None:
            return requested_priority

        existing_priority = self.firewall_repo.get_max_priority_for_source(
            source_application_id, collection_type
        )

        if existing_priority is None:
            return self.PRIORITY_BASELINE.get(collection_type, 100)

        next_priority = existing_priority + self.PRIORITY_INCREMENT
        return min(65000, next_priority)

    def _build_rule_entry(
        self,
        *,
        request: FirewallRequest,
        collection: FirewallRuleCollection,
        collection_type: str,
        rule: Union[ApplicationRuleInput, NetworkRuleInput, NatRuleInput],
        duplicate_key: str,
    ) -> FirewallRuleEntry:
        translated_address: Optional[str] = None
        translated_port_value: Optional[str] = None
        destination_address_column: Optional[str] = None

        if collection_type == "APPLICATION":
            app_rule = cast(ApplicationRuleInput, rule)
            protocols_json = json.dumps(
                [
                    {"port": protocol.port, "type": protocol.type}
                    for protocol in app_rule.protocols
                ]
            )
            source_addresses = json.dumps(app_rule.source_ip_addresses)
            source_ip_groups = json.dumps(app_rule.source_ip_groups)
            destination_addresses = json.dumps(app_rule.destination_addresses)
            destination_fqdns = json.dumps(app_rule.destination_fqdns)
            destination_ports = json.dumps(
                [str(protocol.port) for protocol in app_rule.protocols]
            )
            metadata = json.dumps({"rule_type": "application"})
            ports_value = "|".join(
                str(protocol.port) for protocol in app_rule.protocols
            )
            protocol_value = "APPLICATION"
            direction_value = None
            destination_ip_addresses = json.dumps([])
            destination_ip_groups = json.dumps([])
            destination_address_column = None
            target_fqdns = destination_fqdns
            source_list = app_rule.source_ip_addresses
            destination_value = (
                app_rule.destination_addresses[0]
                if app_rule.destination_addresses
                else (
                    app_rule.destination_fqdns[0]
                    if app_rule.destination_fqdns
                    else None
                )
            )
        elif collection_type == "NETWORK":
            network_rule = cast(NetworkRuleInput, rule)
            protocols_json = json.dumps(network_rule.protocols)
            source_addresses = json.dumps(network_rule.source_ip_addresses)
            source_ip_groups = json.dumps(network_rule.source_ip_groups)
            destination_addresses = json.dumps([])
            destination_ip_addresses = json.dumps(network_rule.destination_ip_addresses)
            destination_ip_groups = json.dumps(network_rule.destination_ip_groups)
            destination_fqdns = json.dumps(network_rule.destination_fqdns)
            destination_ports = json.dumps(network_rule.destination_ports)
            metadata = json.dumps({"rule_type": "network"})
            ports_value = "|".join(network_rule.destination_ports)
            protocol_value = "|".join(network_rule.protocols)
            direction_value = "BIDIRECTIONAL"
            destination_address_column = None
            target_fqdns = destination_fqdns
            source_list = network_rule.source_ip_addresses
            destination_value = (
                network_rule.destination_ip_addresses[0]
                if network_rule.destination_ip_addresses
                else (
                    network_rule.destination_fqdns[0]
                    if network_rule.destination_fqdns
                    else None
                )
            )
        else:  # NAT
            nat_rule = cast(NatRuleInput, rule)
            protocols_json = json.dumps(nat_rule.protocols)
            source_addresses = json.dumps(nat_rule.source_ip_addresses)
            source_ip_groups = json.dumps(nat_rule.source_ip_groups)
            destination_addresses = json.dumps([nat_rule.destination_address])
            destination_ip_addresses = json.dumps([])
            destination_ip_groups = json.dumps([])
            destination_fqdns = json.dumps([])
            destination_ports = json.dumps(nat_rule.destination_ports)
            metadata = json.dumps({"rule_type": "nat"})
            ports_value = "|".join(nat_rule.destination_ports)
            protocol_value = "|".join(nat_rule.protocols)
            direction_value = "INBOUND"
            destination_address_column = nat_rule.destination_address
            target_fqdns = json.dumps([])
            source_list = nat_rule.source_ip_addresses
            destination_value = nat_rule.destination_address
            translated_address = nat_rule.translated_address
            translated_port_value = str(nat_rule.translated_port)

        entry = FirewallRuleEntry(
            firewall_request=request,
            rule_collection=collection,
            collection_type=collection_type,
            name=rule.name,
            ritm_number=getattr(rule, "ritm_number", None),
            description=rule.description,
            source=source_list[0] if source_list else None,
            destination=destination_value,
            ports=ports_value or None,
            protocol=protocol_value or None,
            direction=direction_value,
            protocols=protocols_json,
            source_addresses=source_addresses,
            source_ip_groups=source_ip_groups,
            destination_addresses=destination_addresses,
            destination_ip_addresses=destination_ip_addresses,
            destination_ip_groups=destination_ip_groups,
            destination_fqdns=destination_fqdns,
            destination_ports=destination_ports,
            destination_address=destination_address_column,
            translated_port=translated_port_value,
            translated_address=translated_address,
            target_fqdns=target_fqdns,
            rule_metadata=metadata,
            duplicate_key=duplicate_key,
        )
        return entry

    def _format_rule_for_document(
        self, collection_type: str, entry: FirewallRuleEntry
    ) -> Dict[str, object]:
        protocols = json.loads(entry.protocols) if entry.protocols else []
        source_addresses = (
            json.loads(entry.source_addresses) if entry.source_addresses else []
        )
        source_ip_groups = (
            json.loads(entry.source_ip_groups) if entry.source_ip_groups else []
        )
        destination_addresses = (
            json.loads(entry.destination_addresses)
            if entry.destination_addresses
            else []
        )
        destination_ip_addresses = (
            json.loads(entry.destination_ip_addresses)
            if entry.destination_ip_addresses
            else []
        )
        destination_ip_groups = (
            json.loads(entry.destination_ip_groups)
            if entry.destination_ip_groups
            else []
        )
        destination_fqdns = (
            json.loads(entry.destination_fqdns) if entry.destination_fqdns else []
        )
        destination_ports = (
            json.loads(entry.destination_ports) if entry.destination_ports else []
        )

        base_rule = {
            "name": entry.name,
            "ritm_number": entry.ritm_number or "",
            "description": entry.description or "",
        }

        if collection_type == "APPLICATION":
            base_rule.update(
                {
                    "protocols": protocols,
                    "source_ip_addresses": source_addresses,
                    "source_ip_groups": source_ip_groups,
                    "destination_fqdns": destination_fqdns,
                    "destination_addresses": destination_addresses,
                }
            )
        elif collection_type == "NETWORK":
            base_rule.update(
                {
                    "protocols": protocols,
                    "source_ip_addresses": source_addresses,
                    "source_ip_groups": source_ip_groups,
                    "destination_ip_addresses": destination_ip_addresses,
                    "destination_ip_groups": destination_ip_groups,
                    "destination_ports": destination_ports,
                    "destination_fqdns": destination_fqdns,
                }
            )
        else:  # NAT
            translated_port = (
                int(entry.translated_port)
                if entry.translated_port and str(entry.translated_port).isdigit()
                else entry.translated_port
            )
            base_rule.update(
                {
                    "protocols": protocols,
                    "source_ip_addresses": source_addresses,
                    "source_ip_groups": source_ip_groups,
                    "destination_address": entry.destination_address,
                    "destination_ports": destination_ports,
                    "translated_address": entry.translated_address,
                    "translated_port": translated_port,
                }
            )

        return base_rule

    def _collection_key(self, collection_type: str) -> str:
        return {
            "APPLICATION": "application_rules",
            "NETWORK": "network_rules",
            "NAT": "nat_rules",
        }.get(collection_type, collection_type.lower())

    def _build_collection_document(
        self, request: FirewallRequest
    ) -> Dict[str, Dict[str, object]]:
        ip_groups = json.loads(request.ip_groups) if request.ip_groups else {}
        document: Dict[str, Dict[str, object]] = {
            request.collection_name: {
                "application_name": request.collection_name,
                "ip_groups": ip_groups,
                "rules": {},
            }
        }

        rules_section = cast(
            Dict[str, object], document[request.collection_name]["rules"]
        )

        for collection in request.rule_collections:
            key = self._collection_key(collection.collection_type)
            formatted_rules = [
                self._format_rule_for_document(collection.collection_type, entry)
                for entry in collection.rule_entries
            ]
            if not formatted_rules:
                continue
            rules_section[key] = {
                "priority": collection.priority,
                "action": collection.action,
                "rules": formatted_rules,
            }

        return document

    @staticmethod
    def _build_duplicate_key(
        collection_type: str,
        rule: Union[ApplicationRuleInput, NetworkRuleInput, NatRuleInput],
    ) -> str:
        if collection_type == "APPLICATION":
            typed_rule = cast(ApplicationRuleInput, rule)
            protocol_tokens = "|".join(
                f"{proto.type}:{proto.port}"
                for proto in sorted(
                    typed_rule.protocols, key=lambda p: (p.type, p.port)
                )
            )
            key_components = [
                collection_type,
                typed_rule.name.lower(),
                protocol_tokens,
                "|".join(sorted(typed_rule.source_ip_addresses)),
                "|".join(
                    sorted(
                        typed_rule.destination_fqdns + typed_rule.destination_addresses
                    )
                ),
                "|".join(sorted(typed_rule.source_ip_groups)),
            ]
        elif collection_type == "NETWORK":
            typed_rule = cast(NetworkRuleInput, rule)
            key_components = [
                collection_type,
                typed_rule.name.lower(),
                "|".join(sorted(typed_rule.protocols)),
                "|".join(sorted(typed_rule.source_ip_addresses)),
                "|".join(sorted(typed_rule.source_ip_groups)),
                "|".join(sorted(typed_rule.destination_ip_addresses)),
                "|".join(sorted(typed_rule.destination_ip_groups)),
                "|".join(sorted(typed_rule.destination_ports)),
                "|".join(sorted(typed_rule.destination_fqdns)),
            ]
        else:  # NAT
            typed_rule = cast(NatRuleInput, rule)
            key_components = [
                collection_type,
                typed_rule.name.lower(),
                "|".join(sorted(typed_rule.protocols)),
                "|".join(sorted(typed_rule.source_ip_addresses)),
                "|".join(sorted(typed_rule.source_ip_groups)),
                typed_rule.destination_address.lower(),
                "|".join(sorted(typed_rule.destination_ports)),
                typed_rule.translated_address.lower(),
                str(typed_rule.translated_port),
            ]

        dedupe_string = "::".join(key_components)
        return hashlib.sha256(dedupe_string.encode("utf-8")).hexdigest()

    @staticmethod
    def _build_request_hash(duplicate_keys: Sequence[str]) -> Optional[str]:
        if not duplicate_keys:
            return None
        combined = "::".join(sorted(duplicate_keys))
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()
