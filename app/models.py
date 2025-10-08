"""Database models for TradeX Platform Onboarding."""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum as SQLEnum
import enum

db = SQLAlchemy()


class RequestType(str, enum.Enum):
    """Request type enumeration."""

    ONBOARDING = "ONBOARDING"  # Application onboarding
    FIREWALL = "FIREWALL"  # Firewall rules request
    ORGANIZATION = "ORGANIZATION"  # Add organization
    LOB = "LOB"  # Add Line of Business
    SUBSCRIPTION = "SUBSCRIPTION"  # Add subscription


class RequestStatus(str, enum.Enum):
    """Request status enumeration."""

    DRAFT = "DRAFT"  # Initial draft, can be edited
    PENDING = "PENDING"  # Submitted for approval
    APPROVED = "APPROVED"  # Approved by admin
    REJECTED = "REJECTED"  # Rejected by admin
    CANCELLED = "CANCELLED"  # Cancelled by requester
    SUBSCRIPTION_ASSIGNED = "SUBSCRIPTION_ASSIGNED"  # Subscriptions assigned
    FOUNDATION_INFRA_PROVISIONING = (
        "FOUNDATION_INFRA_PROVISIONING"  # Creating foundation
    )
    FOUNDATION_INFRA_COMPLETED = "FOUNDATION_INFRA_COMPLETED"  # Foundation done
    INFRASTRUCTURE_PROVISIONING = (
        "INFRASTRUCTURE_PROVISIONING"  # Creating infrastructure
    )
    INFRASTRUCTURE_COMPLETED = "INFRASTRUCTURE_COMPLETED"  # Infrastructure done
    COMPLETED = "COMPLETED"  # Handed over to customer
    FAILED = "FAILED"  # Failed at any stage


class WorkflowStage(str, enum.Enum):
    """Workflow stage enumeration."""

    REQUEST_RAISED = "REQUEST_RAISED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    SUBSCRIPTION_ASSIGNMENT = "SUBSCRIPTION_ASSIGNMENT"
    FOUNDATION_INFRA = "FOUNDATION_INFRA"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    NETWORK_REVIEW = "NETWORK_REVIEW"
    RULE_COLLECTION_BUILD = "RULE_COLLECTION_BUILD"
    RULE_DEPLOYMENT = "RULE_DEPLOYMENT"
    HANDOVER = "HANDOVER"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class Application(db.Model):
    """Application model - stores application metadata."""

    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    request_type = db.Column(
        SQLEnum(RequestType), default=RequestType.ONBOARDING, nullable=False, index=True
    )  # Type of request
    app_code = db.Column(
        db.String(50), unique=True, nullable=False, index=True
    )  # Auto-generated (e.g., APP-00001, FW-00001)
    app_slug = db.Column(
        db.String(10), unique=True, nullable=True, index=True
    )  # User provided 4-6 chars (for onboarding only)
    application_name = db.Column(db.String(200), nullable=False)
    organization = db.Column(db.String(100), nullable=True)  # Nullable for some types
    lob = db.Column(db.String(100), nullable=True)  # Line of Business
    onboarding_date = db.Column(db.DateTime, default=datetime.utcnow)
    platform = db.Column(db.String(50), default="Azure")
    status = db.Column(
        SQLEnum(RequestStatus), default=RequestStatus.DRAFT, nullable=False
    )
    current_stage = db.Column(
        SQLEnum(WorkflowStage), default=WorkflowStage.REQUEST_RAISED, nullable=False
    )
    requested_by = db.Column(db.String(200), nullable=False)
    approved_by = db.Column(db.String(200), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    cancelled_by = db.Column(db.String(200), nullable=True)
    cancellation_reason = db.Column(db.Text, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    expedite_requested = db.Column(db.Boolean, default=False, nullable=False)
    expedite_requested_at = db.Column(db.DateTime, nullable=True)
    expedite_reason = db.Column(db.Text, nullable=True)
    is_editable = db.Column(
        db.Boolean, default=True, nullable=False
    )  # Can requester edit?
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    environments = db.relationship(
        "AppEnvironment", backref="application", lazy=True, cascade="all, delete-orphan"
    )
    audits = db.relationship(
        "RequestAudit", backref="application", lazy=True, cascade="all, delete-orphan"
    )
    comments = db.relationship(
        "RequestComment", backref="application", lazy=True, cascade="all, delete-orphan"
    )
    timeline = db.relationship(
        "RequestTimeline",
        backref="application",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        """Convert model to dictionary."""
        firewall_details = getattr(self, "firewall_details", None)
        return {
            "id": self.id,
            "app_code": self.app_code,
            "app_slug": self.app_slug,
            "application_name": self.application_name,
            "organization": self.organization,
            "lob": self.lob,
            "onboarding_date": (
                self.onboarding_date.isoformat() if self.onboarding_date else None
            ),
            "platform": self.platform,
            "request_type": self.request_type.value,
            "status": self.status.value,
            "current_stage": self.current_stage.value,
            "requested_by": self.requested_by,
            "approved_by": self.approved_by,
            "rejection_reason": self.rejection_reason,
            "cancelled_by": self.cancelled_by,
            "cancellation_reason": self.cancellation_reason,
            "cancelled_at": (
                self.cancelled_at.isoformat() if self.cancelled_at else None
            ),
            "expedite_requested": self.expedite_requested,
            "expedite_requested_at": (
                self.expedite_requested_at.isoformat()
                if self.expedite_requested_at
                else None
            ),
            "expedite_reason": self.expedite_reason,
            "is_editable": self.is_editable,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "environments": [env.to_dict() for env in self.environments],  # type: ignore
            "comments": [comment.to_dict() for comment in self.comments],  # type: ignore
            "timeline": [event.to_dict() for event in self.timeline],  # type: ignore
            "firewall_details": (
                firewall_details.to_dict() if firewall_details else None
            ),
        }


class AppEnvironment(db.Model):
    """App Environment model - links applications to environments."""

    __tablename__ = "app_environments"

    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False)
    environment_name = db.Column(db.String(50), nullable=False)
    subscription_id = db.Column(
        db.String(100), nullable=True
    )  # Assigned by admin later
    region = db.Column(db.String(50), default="East US")
    is_assigned = db.Column(db.Boolean, default=False, nullable=False)
    assigned_by = db.Column(db.String(200), nullable=True)
    assigned_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "app_id": self.app_id,
            "environment_name": self.environment_name,
            "subscription_id": self.subscription_id,
            "region": self.region,
            "is_assigned": self.is_assigned,
            "assigned_by": self.assigned_by,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "created_at": self.created_at.isoformat(),
        }


class LookupData(db.Model):
    """Lookup data model - stores reference data."""

    __tablename__ = "lookup"

    id = db.Column(db.Integer, primary_key=True)
    field = db.Column(
        db.String(50), nullable=False, index=True
    )  # Organization, LOB, Environment
    value = db.Column(db.String(100), nullable=False)
    abbreviation = db.Column(db.String(10), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "field": self.field,
            "value": self.value,
            "abbreviation": self.abbreviation,
            "is_active": self.is_active,
        }


class RequestAudit(db.Model):
    """Request audit model - tracks all actions on requests."""

    __tablename__ = "request_audit"

    id = db.Column(db.Integer, primary_key=True)
    request_type = db.Column(
        db.String(50), nullable=False
    )  # CREATE, UPDATE, DELETE, APPROVE
    app_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=True)
    user_email = db.Column(db.String(200), nullable=False)
    action = db.Column(db.String(500), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "request_type": self.request_type,
            "app_id": self.app_id,
            "user_email": self.user_email,
            "action": self.action,
            "details": self.details,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp.isoformat(),
        }


class RequestComment(db.Model):
    """Request comments model - stores comments on requests."""

    __tablename__ = "request_comments"

    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False)
    user_email = db.Column(db.String(200), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    is_internal = db.Column(
        db.Boolean, default=False, nullable=False
    )  # Admin-only comment
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "app_id": self.app_id,
            "user_email": self.user_email,
            "comment": self.comment,
            "is_internal": self.is_internal,
            "created_at": self.created_at.isoformat(),
        }


class RequestTimeline(db.Model):
    """Request timeline model - tracks workflow stages."""

    __tablename__ = "request_timeline"

    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False)
    stage = db.Column(SQLEnum(WorkflowStage), nullable=False)
    status = db.Column(db.String(50), nullable=False)  # IN_PROGRESS, COMPLETED, FAILED
    message = db.Column(db.Text, nullable=True)
    performed_by = db.Column(db.String(200), nullable=True)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "app_id": self.app_id,
            "stage": self.stage.value,
            "status": self.status,
            "message": self.message,
            "performed_by": self.performed_by,
            "created_at": self.created_at.isoformat(),
        }


class FirewallRequest(db.Model):
    """Firewall request model - captures structured firewall rule submissions."""

    __tablename__ = "firewall_requests"

    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(
        db.Integer, db.ForeignKey("applications.id"), nullable=False, unique=True
    )
    source_application_id = db.Column(
        db.Integer, db.ForeignKey("applications.id"), nullable=True
    )
    collection_name = db.Column(db.String(120), nullable=False)
    collection_document = db.Column(db.Text, nullable=True)
    ip_groups = db.Column(db.Text, nullable=True)
    environment_scopes = db.Column(
        db.Text, nullable=False
    )  # JSON array of requested environment scopes
    destination_service = db.Column(db.String(200), nullable=True)
    justification = db.Column(db.Text, nullable=False)
    requested_effective_date = db.Column(db.Date, nullable=True)
    expires_at = db.Column(db.Date, nullable=True)
    github_pr_url = db.Column(db.String(500), nullable=True)
    duplicate_of_request_id = db.Column(
        db.Integer, db.ForeignKey("firewall_requests.id"), nullable=True
    )
    duplicate_hash = db.Column(db.String(128), nullable=True, index=True)
    application_name_at_submission = db.Column(db.String(200), nullable=False)
    organization_at_submission = db.Column(db.String(100), nullable=True)
    lob_at_submission = db.Column(db.String(100), nullable=True)
    requester_email_at_submission = db.Column(db.String(200), nullable=False)
    network_admin_approver = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    application = db.relationship(
        "Application",
        foreign_keys=[app_id],
        backref=db.backref("firewall_details", uselist=False),
        uselist=False,
    )
    source_application = db.relationship(
        "Application",
        foreign_keys=[source_application_id],
        backref="linked_firewall_requests",
    )
    duplicate_of = db.relationship(
        "FirewallRequest", remote_side=[id], backref="duplicates", uselist=False
    )
    rule_collections = db.relationship(
        "FirewallRuleCollection",
        backref="firewall_request",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="FirewallRuleCollection.priority",
    )
    rule_entries = db.relationship(
        "FirewallRuleEntry",
        backref="firewall_request",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="FirewallRuleEntry.id",
    )

    def to_dict(self):
        """Convert model to dictionary."""
        import json

        return {
            "id": self.id,
            "app_id": self.app_id,
            "source_application_id": self.source_application_id,
            "collection_name": self.collection_name,
            "collection_document": self.collection_document,
            "environment_scopes": json.loads(self.environment_scopes),
            "destination_service": self.destination_service,
            "justification": self.justification,
            "requested_effective_date": (
                self.requested_effective_date.isoformat()
                if self.requested_effective_date
                else None
            ),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "github_pr_url": self.github_pr_url,
            "duplicate_of_request_id": self.duplicate_of_request_id,
            "duplicate_hash": self.duplicate_hash,
            "application_name_at_submission": self.application_name_at_submission,
            "organization_at_submission": self.organization_at_submission,
            "lob_at_submission": self.lob_at_submission,
            "requester_email_at_submission": self.requester_email_at_submission,
            "network_admin_approver": self.network_admin_approver,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "ip_groups": json.loads(self.ip_groups) if self.ip_groups else {},
            "rule_entries": [entry.to_dict() for entry in self.rule_entries],
            "rule_collections": [
                collection.to_dict() for collection in self.rule_collections
            ],
        }


class FirewallRuleCollection(db.Model):
    """Grouping for firewall rules sharing type, action, and priority."""

    __tablename__ = "firewall_rule_collections"

    id = db.Column(db.Integer, primary_key=True)
    firewall_request_id = db.Column(
        db.Integer,
        db.ForeignKey("firewall_requests.id"),
        nullable=False,
        index=True,
    )
    collection_type = db.Column(db.String(20), nullable=False)
    action = db.Column(db.String(20), nullable=False)
    priority = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    rule_entries = db.relationship(
        "FirewallRuleEntry",
        backref="rule_collection",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="FirewallRuleEntry.id",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "collection_type": self.collection_type,
            "action": self.action,
            "priority": self.priority,
            "rules": [entry.to_dict() for entry in self.rule_entries],
        }


class FirewallRuleEntry(db.Model):
    """Individual firewall rule entry belonging to a firewall request."""

    __tablename__ = "firewall_rule_entries"

    id = db.Column(db.Integer, primary_key=True)
    firewall_request_id = db.Column(
        db.Integer, db.ForeignKey("firewall_requests.id"), nullable=False, index=True
    )
    rule_collection_id = db.Column(
        db.Integer,
        db.ForeignKey("firewall_rule_collections.id"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(128), nullable=False)
    ritm_number = db.Column(db.String(64), nullable=True)
    description = db.Column(db.String(500), nullable=True)
    collection_type = db.Column(db.String(20), nullable=False, default="NETWORK")
    source = db.Column(db.String(255), nullable=True)
    destination = db.Column(db.String(255), nullable=True)
    ports = db.Column(db.String(200), nullable=True)
    protocol = db.Column(db.String(20), nullable=True)
    direction = db.Column(db.String(20), nullable=True)
    protocols = db.Column(db.Text, nullable=False)
    source_addresses = db.Column(db.Text, nullable=False)
    source_ip_groups = db.Column(db.Text, nullable=True)
    destination_addresses = db.Column(db.Text, nullable=True)
    destination_ip_addresses = db.Column(db.Text, nullable=True)
    destination_ip_groups = db.Column(db.Text, nullable=True)
    destination_fqdns = db.Column(db.Text, nullable=True)
    destination_ports = db.Column(db.Text, nullable=True)
    destination_address = db.Column(db.String(255), nullable=True)
    translated_address = db.Column(db.String(255), nullable=True)
    translated_port = db.Column(db.String(50), nullable=True)
    target_fqdns = db.Column(db.Text, nullable=True)
    rule_metadata = db.Column("metadata", db.Text, nullable=True)
    duplicate_key = db.Column(db.String(128), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Convert model to dictionary."""
        import json

        def _loads(value, default):
            try:
                return json.loads(value) if value else default
            except (TypeError, ValueError):
                return default

        return {
            "id": self.id,
            "firewall_request_id": self.firewall_request_id,
            "rule_collection_id": self.rule_collection_id,
            "name": self.name,
            "ritm_number": self.ritm_number,
            "description": self.description,
            "source": self.source,
            "destination": self.destination,
            "ports": self.ports.split("|") if self.ports else [],
            "protocol": self.protocol,
            "direction": self.direction,
            "collection_type": self.collection_type,
            "protocols": _loads(self.protocols, []),
            "source_addresses": _loads(self.source_addresses, []),
            "source_ip_groups": _loads(self.source_ip_groups, []),
            "destination_addresses": _loads(self.destination_addresses, []),
            "destination_ip_addresses": _loads(self.destination_ip_addresses, []),
            "destination_ip_groups": _loads(self.destination_ip_groups, []),
            "destination_fqdns": _loads(self.destination_fqdns, []),
            "destination_ports": _loads(self.destination_ports, []),
            "destination_address": self.destination_address,
            "translated_address": self.translated_address,
            "translated_port": self.translated_port,
            "target_fqdns": _loads(self.target_fqdns, []),
            "metadata": _loads(self.rule_metadata, {}),
            "duplicate_key": self.duplicate_key,
            "created_at": self.created_at.isoformat(),
        }


class SubscriptionManagement(db.Model):
    """Subscription management model - tracks Azure subscriptions with ownership."""

    __tablename__ = "subscription_management"

    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(
        db.Integer, db.ForeignKey("applications.id"), nullable=False, unique=True
    )
    subscription_name = db.Column(db.String(200), nullable=False)
    subscription_id = db.Column(
        db.String(100), nullable=False, unique=True
    )  # Azure subscription GUID
    owner_emails = db.Column(db.Text, nullable=False)  # JSON array of owner emails
    creator_email = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationship
    application = db.relationship(
        "Application", backref="subscription_details", uselist=False
    )

    def to_dict(self):
        """Convert model to dictionary."""
        import json

        return {
            "id": self.id,
            "app_id": self.app_id,
            "subscription_name": self.subscription_name,
            "subscription_id": self.subscription_id,
            "owner_emails": json.loads(self.owner_emails),
            "creator_email": self.creator_email,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
