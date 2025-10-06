"""Application service - business logic for application management."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from flask_sqlalchemy import SQLAlchemy

from app.models import (
    Application,
    AppEnvironment,
    RequestStatus,
    RequestType,
    WorkflowStage,
)
from app.repositories import (
    ApplicationRepository,
    AuditRepository,
    CommentRepository,
    TimelineRepository,
)


class ApplicationService:
    """Service for application business logic."""

    def __init__(self, db: SQLAlchemy) -> None:
        """Initialize application service.

        Args:
            db: SQLAlchemy database instance
        """
        self.db = db
        self.app_repo = ApplicationRepository(db)
        self.audit_repo = AuditRepository(db)
        self.comment_repo = CommentRepository(db)
        self.timeline_repo = TimelineRepository(db)

    def create_application(
        self, data: Dict[str, Any], requested_by: str, ip_address: Optional[str] = None
    ) -> Application:
        """Create a new application request.

        Args:
            data: Application creation data dictionary
            requested_by: Email of requester
            ip_address: IP address of requester

        Returns:
            Created application instance

        Raises:
            ValueError: If slug is already taken or validation fails
        """
        request_type = data.get("request_type", RequestType.ONBOARDING)

        # Validate slug uniqueness for onboarding requests
        if request_type == RequestType.ONBOARDING:
            app_slug = data.get("app_slug")
            if app_slug and not self.is_slug_available(app_slug):
                raise ValueError(f"Slug '{app_slug}' is already taken")

        # Generate app code
        app_code = self._generate_app_code(request_type)

        # Create application
        app_data = {
            k: v
            for k, v in data.items()
            if k not in ("environments", "region", "save_as_draft")
        }
        app_data["app_code"] = app_code
        app_data["requested_by"] = requested_by

        # Convert application_name to title case
        if "application_name" in app_data:
            app_data["application_name"] = app_data["application_name"].title()

        # Check if user wants to save as draft
        save_as_draft = data.get("save_as_draft", False)
        if save_as_draft:
            app_data["status"] = RequestStatus.DRAFT
            app_data["current_stage"] = WorkflowStage.REQUEST_RAISED
            app_data["is_editable"] = True
        else:
            # Default: submit directly for approval
            app_data["status"] = RequestStatus.PENDING
            app_data["current_stage"] = WorkflowStage.PENDING_APPROVAL
            app_data["is_editable"] = False

        application = Application(**app_data)

        # Add environments if provided
        environments = data.get("environments", [])
        if environments:
            for env_name in environments:
                env = AppEnvironment(
                    environment_name=env_name, region=data.get("region", "East US")
                )
                application.environments.append(env)

        # Save application
        self.app_repo.db.session.add(application)
        self.app_repo.commit()

        # Create audit log
        self._create_audit_log(
            request_type="CREATE",
            app_id=application.id,
            user_email=requested_by,
            action=f"Created {request_type.value} request: {app_code}",
            details=f"Application: {data.get('application_name', 'N/A')}",
            ip_address=ip_address,
        )

        # Create initial timeline event
        self._create_timeline_event(
            app_id=application.id,
            stage=WorkflowStage.REQUEST_RAISED,
            status="COMPLETED",
            message="Request created",
            performed_by=requested_by,
        )

        # If not saved as draft, add submission timeline event
        if not save_as_draft:
            self._create_timeline_event(
                app_id=application.id,
                stage=WorkflowStage.PENDING_APPROVAL,
                status="IN_PROGRESS",
                message="Request submitted for approval",
                performed_by=requested_by,
            )

        return application

    def submit_application(
        self,
        app_id: int,
        user_email: str,
        is_admin: bool = False,
        ip_address: Optional[str] = None,
    ) -> Application:
        """Submit a draft application for approval.

        Args:
            app_id: Application ID
            user_email: Email of submitting user
            is_admin: Whether submitting user is an admin
            ip_address: Optional IP address for audit trail

        Returns:
            Updated application instance

        Raises:
            ValueError: If application not found or already submitted
            PermissionError: If user is not authorized to submit
        """

        application = self.app_repo.get_by_id(app_id)
        if not application:
            raise ValueError(f"Application {app_id} not found")

        if application.status != RequestStatus.DRAFT:
            raise ValueError("Only draft requests can be submitted for approval")

        if application.requested_by != user_email and not is_admin:
            raise PermissionError("You are not authorized to submit this request")

        application.status = RequestStatus.PENDING
        application.current_stage = WorkflowStage.PENDING_APPROVAL
        application.is_editable = False
        application.updated_at = datetime.utcnow()

        self.app_repo.commit()

        self._create_audit_log(
            request_type="SUBMIT",
            app_id=app_id,
            user_email=user_email,
            action=f"Submitted request {application.app_code} for approval",
            details="Request moved to pending approval",
            ip_address=ip_address,
        )

        self._create_timeline_event(
            app_id=app_id,
            stage=WorkflowStage.PENDING_APPROVAL,
            status="IN_PROGRESS",
            message="Request submitted for approval",
            performed_by=user_email,
        )

        return application

    def update_application(
        self,
        app_id: int,
        data: Dict[str, Any],
        user_email: str,
        is_admin: bool = False,
        ip_address: Optional[str] = None,
    ) -> Application:
        """Update an existing application.

        Args:
            app_id: Application ID
            data: Update data
            user_email: Email of user making update
            is_admin: Whether user is an admin
            ip_address: IP address of user

        Returns:
            Updated application instance

        Raises:
            ValueError: If application not found or not editable
            PermissionError: If user is not authorized to update
        """
        application = self.app_repo.get_by_id(app_id)
        if not application:
            raise ValueError(f"Application {app_id} not found")

        # Check authorization: only requester or admin can update
        if not is_admin and application.requested_by != user_email:
            raise PermissionError("You are not authorized to update this request")

        if not application.is_editable:
            raise ValueError("Application is no longer editable")

        # Handle save_as_draft flag
        save_as_draft = data.get("save_as_draft", False)

        # Update fields (excluding non-model fields)
        for key, value in data.items():
            if key in ("save_as_draft", "environments", "region"):
                continue  # Skip non-model fields
            if hasattr(application, key) and key not in (
                "id",
                "app_code",
                "created_at",
            ):
                setattr(application, key, value)

        # Update status based on save_as_draft flag if not explicitly set
        if "status" not in data:
            if save_as_draft:
                application.status = RequestStatus.DRAFT
                application.is_editable = True
            else:
                application.status = RequestStatus.PENDING
                application.current_stage = WorkflowStage.PENDING_APPROVAL
                application.is_editable = False

        application.updated_at = datetime.utcnow()
        self.app_repo.commit()

        # Create audit log
        self._create_audit_log(
            request_type="UPDATE",
            app_id=app_id,
            user_email=user_email,
            action=f"Updated application {application.app_code}",
            details=f"Fields updated: {', '.join(data.keys())}",
            ip_address=ip_address,
        )

        return application

    def get_application(self, app_id: int) -> Optional[Application]:
        """Get application by ID.

        Args:
            app_id: Application ID

        Returns:
            Application instance or None
        """
        return self.app_repo.get_by_id(app_id)

    def get_application_by_code(self, app_code: str) -> Optional[Application]:
        """Get application by app code.

        Args:
            app_code: Application code

        Returns:
            Application instance or None
        """
        return self.app_repo.get_by_app_code(app_code)

    def list_applications(
        self,
        status: Optional[RequestStatus] = None,
        request_type: Optional[RequestType] = None,
        requester: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Application]:
        """List applications with optional filters.

        Args:
            status: Filter by status
            request_type: Filter by request type
            requester: Filter by requester email
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of applications
        """
        if status:
            return self.app_repo.get_by_status(status, skip, limit)
        elif request_type:
            return self.app_repo.get_by_type(request_type, skip, limit)
        elif requester:
            return self.app_repo.get_by_requester(requester, skip, limit)
        else:
            return self.app_repo.get_all(skip, limit)

    def is_slug_available(self, slug: str) -> bool:
        """Check if slug is available.

        Args:
            slug: Slug to check

        Returns:
            True if available, False otherwise
        """
        return self.app_repo.is_slug_available(slug)

    def get_dashboard_stats(self) -> Dict[str, int]:
        """Get dashboard statistics.

        Returns:
            Dictionary with counts by status
        """
        return {
            "total": self.app_repo.query().count(),
            "draft": self.app_repo.count_by_status(RequestStatus.DRAFT),
            "pending": self.app_repo.count_by_status(RequestStatus.PENDING),
            "approved": self.app_repo.count_by_status(RequestStatus.APPROVED),
            "completed": self.app_repo.count_by_status(RequestStatus.COMPLETED),
            "rejected": self.app_repo.count_by_status(RequestStatus.REJECTED),
        }

    def _generate_app_code(self, request_type: RequestType) -> str:
        """Generate unique app code based on request type.

        Args:
            request_type: Request type enum

        Returns:
            Generated app code
        """
        # Get prefix based on request type
        prefix_map = {
            RequestType.ONBOARDING: "APP",
            RequestType.FIREWALL: "FW",
            RequestType.ORGANIZATION: "ORG",
            RequestType.LOB: "LOB",
            RequestType.SUBSCRIPTION: "SUB",
        }
        prefix = prefix_map.get(request_type, "REQ")

        # Get latest application of this type
        latest_app = self.app_repo.get_latest_by_type(request_type)

        if latest_app and latest_app.id:
            # Extract number from last app code and increment
            next_num = latest_app.id + 1
        else:
            next_num = 1

        return f"{prefix}-{next_num:05d}"

    def _create_audit_log(
        self,
        request_type: str,
        app_id: int,
        user_email: str,
        action: str,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Create an audit log entry.

        Args:
            request_type: Type of request (CREATE, UPDATE, etc.)
            app_id: Application ID
            user_email: User email
            action: Action description
            details: Additional details
            ip_address: IP address
        """
        from app.models import RequestAudit

        audit = RequestAudit(
            request_type=request_type,
            app_id=app_id,
            user_email=user_email,
            action=action,
            details=details,
            ip_address=ip_address,
        )
        self.audit_repo.create(audit)
        self.audit_repo.commit()

    def _create_timeline_event(
        self,
        app_id: int,
        stage: WorkflowStage,
        status: str,
        message: Optional[str] = None,
        performed_by: Optional[str] = None,
    ) -> None:
        """Create a timeline event.

        Args:
            app_id: Application ID
            stage: Workflow stage
            status: Status (IN_PROGRESS, COMPLETED, FAILED)
            message: Event message
            performed_by: User who performed action
        """
        from app.models import RequestTimeline

        event = RequestTimeline(
            app_id=app_id,
            stage=stage,
            status=status,
            message=message,
            performed_by=performed_by,
        )
        self.timeline_repo.create(event)
        self.timeline_repo.commit()

    def cancel_application(
        self,
        app_id: int,
        user_email: str,
        is_admin: bool,
        cancellation_reason: str,
        ip_address: Optional[str] = None,
    ) -> Application:
        """Cancel a request (DRAFT or PENDING status only).

        Args:
            app_id: Application ID
            user_email: Email of user cancelling
            is_admin: Whether user is an admin
            cancellation_reason: Reason for cancellation
            ip_address: IP address of user

        Returns:
            Cancelled application instance

        Raises:
            ValueError: If application not found or cannot be cancelled
            PermissionError: If user not authorized
        """
        application = self.app_repo.get_by_id(app_id)
        if not application:
            raise ValueError(f"Application {app_id} not found")

        # Check authorization: only requester or admin can cancel
        if not is_admin and application.requested_by != user_email:
            raise PermissionError("You are not authorized to cancel this request")

        # Check if status allows cancellation
        if application.status not in [RequestStatus.DRAFT, RequestStatus.PENDING]:
            raise ValueError(
                f"Cannot cancel request with status {application.status.value}"
            )

        # Update application
        application.status = RequestStatus.CANCELLED
        application.current_stage = WorkflowStage.CANCELLED
        application.cancelled_by = user_email
        application.cancellation_reason = cancellation_reason
        application.cancelled_at = datetime.utcnow()
        application.is_editable = False
        application.updated_at = datetime.utcnow()

        self.app_repo.commit()

        # Create audit log
        self._create_audit_log(
            request_type="CANCEL",
            app_id=app_id,
            user_email=user_email,
            action=f"Cancelled request {application.app_code}",
            details=f"Reason: {cancellation_reason}",
            ip_address=ip_address,
        )

        # Create timeline event
        self._create_timeline_event(
            app_id=app_id,
            stage=WorkflowStage.CANCELLED,
            status="COMPLETED",
            message=f"Request cancelled: {cancellation_reason}",
            performed_by=user_email,
        )

        return application

    def expedite_application(
        self,
        app_id: int,
        user_email: str,
        is_admin: bool,
        expedite_reason: str,
        ip_address: Optional[str] = None,
    ) -> Application:
        """Request expedite processing for a pending request.

        Args:
            app_id: Application ID
            user_email: Email of user requesting expedite
            is_admin: Whether user is an admin
            expedite_reason: Reason for expedite request
            ip_address: IP address of user

        Returns:
            Application instance with expedite flag set

        Raises:
            ValueError: If application not found or cannot be expedited
            PermissionError: If user not authorized
        """
        application = self.app_repo.get_by_id(app_id)
        if not application:
            raise ValueError(f"Application {app_id} not found")

        # Check authorization: only requester or admin can expedite
        if not is_admin and application.requested_by != user_email:
            raise PermissionError("You are not authorized to expedite this request")

        # Check if status allows expedite
        if application.status != RequestStatus.PENDING:
            raise ValueError(
                f"Cannot expedite request with status {application.status.value}"
            )

        # Check if already expedited
        if application.expedite_requested:
            raise ValueError("Expedite has already been requested for this application")

        # Update application
        application.expedite_requested = True
        application.expedite_requested_at = datetime.utcnow()
        application.expedite_reason = expedite_reason
        application.updated_at = datetime.utcnow()

        self.app_repo.commit()

        # Create audit log
        self._create_audit_log(
            request_type="EXPEDITE",
            app_id=app_id,
            user_email=user_email,
            action=f"Expedite requested for {application.app_code}",
            details=f"Reason: {expedite_reason}",
            ip_address=ip_address,
        )

        # Create timeline event
        self._create_timeline_event(
            app_id=app_id,
            stage=application.current_stage,
            status="IN_PROGRESS",
            message=f"Expedite requested: {expedite_reason}",
            performed_by=user_email,
        )

        return application
