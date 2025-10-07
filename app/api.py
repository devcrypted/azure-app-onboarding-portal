"""API Blueprint - RESTful API endpoints using service layer (Refactored).

This module provides REST API endpoints for the TradeX Platform Onboarding application.
All business logic has been moved to the service layer following SOLID principles.
"""

from datetime import datetime
from typing import Any, Dict

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from app.models import RequestStatus, RequestType, WorkflowStage, db
from app.repositories import AuditRepository
from app.schemas import (
    ApprovalRequest,
    FirewallRequestCreate,
    LookupDataCreate,
    OnboardingRequest,
)
from app.services import (
    ApplicationService,
    AuthService,
    FirewallRequestService,
    LookupService,
)
from app.services.firewall_request_service import DuplicateFirewallRuleError

api_bp = Blueprint("api", __name__, url_prefix="/api")


# ============================================================================
# Helper Functions
# ============================================================================


def get_current_user_email() -> str:
    """Get current user email from request headers or session.

    In production, this would extract from Azure AD JWT token.
    """
    return request.headers.get("X-User-Email", "guest@tradexfoods.com")


def get_services() -> Dict[str, Any]:
    """Get all service instances.

    Returns:
        Dictionary with service instances
    """
    return {
        "app": ApplicationService(db),
        "auth": AuthService(),
        "lookup": LookupService(db),
        "firewall": FirewallRequestService(db),
    }


# ============================================================================
# Health & Utility Endpoints
# ============================================================================


@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})


@api_bp.route("/validate/slug/<slug>", methods=["GET"])
def validate_slug(slug: str):
    """Validate app slug uniqueness and format.

    Args:
        slug: Application slug to validate

    Returns:
        JSON response with availability status
    """
    try:
        services = get_services()

        # Sanitize and format slug
        slug = slug.strip().lower()

        # Validate format (alphanumeric only, 4-6 chars)
        if not slug or len(slug) < 4 or len(slug) > 6:
            return (
                jsonify(
                    {
                        "available": False,
                        "message": "Slug must be between 4 and 6 characters",
                    }
                ),
                400,
            )

        if not slug.isalnum():
            return (
                jsonify(
                    {
                        "available": False,
                        "message": "Slug must contain only alphanumeric characters",
                    }
                ),
                400,
            )

        # Check uniqueness using service
        is_available = services["app"].is_slug_available(slug)

        if is_available:
            return jsonify({"available": True, "message": "Slug is available"}), 200
        else:
            return (
                jsonify({"available": False, "message": "This slug is already taken"}),
                200,
            )

    except Exception as e:
        return (
            jsonify({"available": False, "message": f"Validation error: {str(e)}"}),
            500,
        )


# ============================================================================
# Application Request Endpoints
# ============================================================================


@api_bp.route("/requests", methods=["GET"])
def get_requests():
    """Get all onboarding requests.

    Admins see all requests, regular users see only their own.

    Returns:
        JSON list of applications
    """
    user_email = get_current_user_email()
    services = get_services()

    request_type_filter = request.args.get("type")
    status_filter = request.args.get("status")
    is_admin = services["auth"].is_admin(user_email)
    is_network_admin = services["auth"].is_network_admin(user_email)

    try:
        request_type = (
            RequestType[request_type_filter.upper()] if request_type_filter else None
        )
    except KeyError:
        return (
            jsonify({"error": f"Unknown request type '{request_type_filter}'"}),
            400,
        )

    try:
        status = RequestStatus[status_filter.upper()] if status_filter else None
    except KeyError:
        return (
            jsonify({"error": f"Unknown status '{status_filter}'"}),
            400,
        )

    if is_admin or is_network_admin:
        applications = services["app"].list_applications()
    else:
        applications = services["app"].list_applications(requester=user_email)

    if request_type:
        applications = [app for app in applications if app.request_type == request_type]

    if status:
        applications = [app for app in applications if app.status == status]

    return jsonify({"requests": [app.to_dict() for app in applications]})


@api_bp.route("/requests/<int:request_id>", methods=["GET"])
def get_request(request_id: int):
    """Get specific onboarding request with audit logs.

    Args:
        request_id: Application ID

    Returns:
        JSON application details with audit logs
    """
    user_email = get_current_user_email()
    services = get_services()

    application = services["app"].get_application(request_id)
    if not application:
        return jsonify({"error": "Application not found"}), 404

    # Check authorization
    if (
        not services["auth"].is_admin(user_email)
        and application.requested_by != user_email
    ):
        return jsonify({"error": "Unauthorized"}), 403

    # Get audit logs
    audit_repo = AuditRepository(db)
    audit_logs = audit_repo.get_by_app_id(request_id)

    # Build response
    result = application.to_dict()
    result["audit_logs"] = [log.to_dict() for log in audit_logs]

    return jsonify(result)


@api_bp.route("/requests", methods=["POST"])
def create_request():
    """Create new onboarding request.

    Validates input data and creates application with environments.

    Returns:
        JSON with created application details
    """
    user_email = get_current_user_email()
    services = get_services()

    try:
        # Validate request data
        data = OnboardingRequest(**request.json)  # type: ignore

        # Prepare data for service
        app_data = {
            "request_type": RequestType.ONBOARDING,
            "app_slug": data.app_slug,
            "application_name": data.application_name,
            "organization": data.organization,
            "lob": data.lob,
            "platform": data.platform,
            "environments": [env.environment_name for env in data.environments],
            "region": data.environments[0].region if data.environments else "East US",
            "save_as_draft": data.save_as_draft,
        }

        # Create application using service
        application = services["app"].create_application(
            data=app_data,
            requested_by=user_email,
            ip_address=request.remote_addr,
        )

        return (
            jsonify(
                {
                    "message": "Onboarding request created successfully",
                    "request_id": application.id,
                    "app_code": application.app_code,
                    "app_slug": application.app_slug,
                }
            ),
            201,
        )

    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/requests/firewall", methods=["POST"])
def create_firewall_request():
    """Create a new firewall request."""

    user_email = get_current_user_email()
    services = get_services()

    try:
        payload = FirewallRequestCreate(**request.json)  # type: ignore[arg-type]
        firewall_request = services["firewall"].create_firewall_request(
            payload,
            requested_by=user_email,
            ip_address=request.remote_addr,
        )

        application = firewall_request.application

        return (
            jsonify(
                {
                    "message": "Firewall request submitted successfully",
                    "request_id": firewall_request.id,
                    "app_id": application.id,
                    "app_code": application.app_code,
                    "application_status": application.status.value,
                    "firewall_request": firewall_request.to_dict(),
                }
            ),
            201,
        )

    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except DuplicateFirewallRuleError as e:
        return jsonify({"error": str(e), "duplicates": e.duplicates}), 409
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/requests/firewall", methods=["GET"])
def list_firewall_requests():
    """List firewall requests for the caller or all if authorized."""

    user_email = get_current_user_email()
    services = get_services()

    is_admin = services["auth"].is_admin(user_email)
    is_network_admin = services["auth"].is_network_admin(user_email)
    include_all = is_admin or is_network_admin

    firewall_requests = services["firewall"].list_requests(
        user_email=user_email, include_all=include_all
    )

    return jsonify(
        {
            "requests": [
                firewall_request.to_dict() for firewall_request in firewall_requests
            ],
            "visibility": "all" if include_all else "own",
        }
    )


@api_bp.route("/requests/<int:request_id>/submit", methods=["POST"])
def submit_request(request_id: int):
    """Submit a draft onboarding request for approval."""

    user_email = get_current_user_email()
    services = get_services()

    try:
        is_admin = services["auth"].is_admin(user_email)
        application = services["app"].submit_application(
            app_id=request_id,
            user_email=user_email,
            is_admin=is_admin,
            ip_address=request.remote_addr,
        )

        return (
            jsonify(
                {
                    "message": "Request submitted for approval",
                    "status": application.status.value,
                    "current_stage": application.current_stage.value,
                }
            ),
            200,
        )

    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/requests/<int:request_id>", methods=["PATCH"])
def update_request(request_id: int):
    """Update a draft onboarding request.

    Only draft requests (status=DRAFT, is_editable=True) can be updated.
    Only the requester or admins can update a request.

    Args:
        request_id: Application ID

    Returns:
        JSON with updated application details
    """
    user_email = get_current_user_email()
    services = get_services()

    try:
        is_admin = services["auth"].is_admin(user_email)

        # Validate request data
        data = OnboardingRequest(**request.json)  # type: ignore

        # Prepare data for service
        app_data = {
            "request_type": RequestType.ONBOARDING,
            "app_slug": data.app_slug,
            "application_name": data.application_name,
            "organization": data.organization,
            "lob": data.lob,
            "platform": data.platform,
            "environments": [env.environment_name for env in data.environments],
            "region": data.environments[0].region if data.environments else "East US",
            "save_as_draft": data.save_as_draft,
        }

        # Update application using service
        application = services["app"].update_application(
            app_id=request_id,
            data=app_data,
            user_email=user_email,
            is_admin=is_admin,
            ip_address=request.remote_addr,
        )

        return (
            jsonify(
                {
                    "message": "Request updated successfully",
                    "request_id": application.id,
                    "app_code": application.app_code,
                    "app_slug": application.app_slug,
                    "status": application.status.value,
                }
            ),
            200,
        )

    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/requests/<int:request_id>/approve", methods=["POST"])
def approve_request(request_id: int):
    """Approve or reject onboarding request (Admin only).

    Args:
        request_id: Application ID

    Returns:
        JSON with approval status
    """
    user_email = get_current_user_email()
    services = get_services()

    # Check admin authorization
    if not services["auth"].is_admin(user_email):
        return jsonify({"error": "Unauthorized - Admin access required"}), 403

    try:
        # Validate approval data
        approval_data = ApprovalRequest(**request.json)  # type: ignore

        # TODO: Implement approve/reject methods in ApplicationService
        # For now, use direct repository access
        from app.repositories import ApplicationRepository, TimelineRepository

        app_repo = ApplicationRepository(db)
        timeline_repo = TimelineRepository(db)

        application = app_repo.get_by_id(request_id)
        if not application:
            return jsonify({"error": "Application not found"}), 404

        # Check if already processed
        if application.status != RequestStatus.PENDING:
            return (
                jsonify({"error": f"Request already {application.status.value}"}),
                400,
            )

        # Update application status
        if approval_data.approved:
            application.status = RequestStatus.APPROVED
            application.approved_by = user_email
            application.onboarding_date = datetime.utcnow()
            application.current_stage = WorkflowStage.SUBSCRIPTION_ASSIGNMENT
            message = f"Request approved by {user_email}"
        else:
            application.status = RequestStatus.REJECTED
            application.approved_by = user_email
            application.rejection_reason = approval_data.rejection_reason
            application.current_stage = WorkflowStage.REJECTED
            message = (
                f"Request rejected by {user_email}: {approval_data.rejection_reason}"
            )

        app_repo.commit()

        # Create timeline events
        from app.models import RequestTimeline

        timeline_events = []

        if approval_data.approved:
            timeline_events.append(
                RequestTimeline(  # type: ignore
                    app_id=request_id,
                    stage=WorkflowStage.PENDING_APPROVAL,
                    status="COMPLETED",
                    message=message,
                    performed_by=user_email,
                )
            )
            timeline_events.append(
                RequestTimeline(  # type: ignore
                    app_id=request_id,
                    stage=WorkflowStage.APPROVED,
                    status="COMPLETED",
                    message=f"Request approved by {user_email}",
                    performed_by=user_email,
                )
            )
            timeline_events.append(
                RequestTimeline(  # type: ignore
                    app_id=request_id,
                    stage=WorkflowStage.SUBSCRIPTION_ASSIGNMENT,
                    status="IN_PROGRESS",
                    message="Subscription assignment started",
                    performed_by=user_email,
                )
            )
        else:
            timeline_events.append(
                RequestTimeline(  # type: ignore
                    app_id=request_id,
                    stage=WorkflowStage.PENDING_APPROVAL,
                    status="FAILED",
                    message=message,
                    performed_by=user_email,
                )
            )
            timeline_events.append(
                RequestTimeline(  # type: ignore
                    app_id=request_id,
                    stage=WorkflowStage.REJECTED,
                    status="FAILED",
                    message=message,
                    performed_by=user_email,
                )
            )

        for event in timeline_events:
            timeline_repo.create(event)

        timeline_repo.commit()

        return jsonify(
            {
                "message": "Request processed successfully",
                "status": application.status.value,
            }
        )

    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/requests/<int:request_id>/assign-subscriptions", methods=["POST"])
def assign_subscriptions(request_id: int):
    """Assign subscription IDs to environments (Admin only).

    Args:
        request_id: Application ID

    Returns:
        JSON with assignment status
    """
    user_email = get_current_user_email()
    services = get_services()

    # Check admin authorization
    if not services["auth"].is_admin(user_email):
        return jsonify({"error": "Unauthorized - Admin access required"}), 403

    try:
        # TODO: Implement in ApplicationService
        # For now, use direct database access
        from app.models import AppEnvironment, Application, RequestTimeline

        application = Application.query.get_or_404(request_id)

        # Check if request is approved
        if application.status != RequestStatus.APPROVED:
            return jsonify({"error": "Request must be approved first"}), 400

        # Get subscription assignments from request body
        assignments = request.json.get("assignments", [])
        if not assignments:
            return jsonify({"error": "No subscription assignments provided"}), 400

        # Update each environment with subscription ID
        for assignment in assignments:
            env_id = assignment.get("env_id")
            subscription_id = assignment.get("subscription_id")

            if not env_id or not subscription_id:
                continue

            environment = AppEnvironment.query.filter_by(
                id=env_id, app_id=request_id
            ).first()

            if environment:
                environment.subscription_id = subscription_id
                environment.is_assigned = True
                environment.assigned_by = user_email
                environment.assigned_at = datetime.utcnow()

        # Check if all environments have subscriptions
        all_envs = AppEnvironment.query.filter_by(app_id=request_id).all()
        all_assigned = all([env.is_assigned for env in all_envs])

        timeline_events = []

        if (
            all_assigned
            and application.current_stage == WorkflowStage.SUBSCRIPTION_ASSIGNMENT
        ):
            previous_stage = application.current_stage
            application.current_stage = WorkflowStage.FOUNDATION_INFRA
            application.status = RequestStatus.FOUNDATION_INFRA_PROVISIONING
            application.updated_at = datetime.utcnow()

            timeline_events.append(
                RequestTimeline(  # type: ignore
                    app_id=request_id,
                    stage=previous_stage,
                    status="COMPLETED",
                    message="Subscriptions assigned to all environments",
                    performed_by=user_email,
                )
            )
            timeline_events.append(
                RequestTimeline(  # type: ignore
                    app_id=request_id,
                    stage=WorkflowStage.FOUNDATION_INFRA,
                    status="IN_PROGRESS",
                    message="Foundation infrastructure provisioning started",
                    performed_by=user_email,
                )
            )

        for event in timeline_events:
            db.session.add(event)

        db.session.commit()

        return jsonify(
            {
                "message": "Subscriptions assigned successfully",
                "all_assigned": all_assigned,
                "current_stage": application.current_stage.value,
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/requests/<int:request_id>/advance-stage", methods=["POST"])
def advance_stage(request_id: int):
    """Advance request through workflow stages (Admin only).

    Args:
        request_id: Application ID

    Returns:
        JSON with stage advancement status
    """
    user_email = get_current_user_email()
    services = get_services()

    if not services["auth"].is_admin(user_email):
        return jsonify({"error": "Unauthorized - Admin access required"}), 403

    try:
        # TODO: Implement in ApplicationService as advance_workflow_stage()
        from app.models import Application, RequestTimeline

        data = request.json or {}
        action = data.get("action")

        application = Application.query.get_or_404(request_id)

        previous_stage = application.current_stage
        completion_message = ""
        next_stage_message = None
        response_message = ""
        next_stage = None

        if action == "foundation-complete":
            if application.current_stage != WorkflowStage.FOUNDATION_INFRA:
                return jsonify({"error": "Invalid stage for this action"}), 400

            next_stage = WorkflowStage.INFRASTRUCTURE
            application.status = RequestStatus.INFRASTRUCTURE_PROVISIONING
            completion_message = "Foundation infrastructure completed."
            next_stage_message = "Application infrastructure provisioning started."
            response_message = "Foundation infrastructure marked complete, moved to Application Infrastructure"

        elif action == "infrastructure-complete":
            if application.current_stage != WorkflowStage.INFRASTRUCTURE:
                return jsonify({"error": "Invalid stage for this action"}), 400

            next_stage = WorkflowStage.HANDOVER
            application.status = RequestStatus.INFRASTRUCTURE_COMPLETED
            completion_message = "Application infrastructure completed."
            next_stage_message = "Handover phase initiated."
            response_message = (
                "Application infrastructure marked complete, moved to Handover"
            )

        elif action == "handover-complete":
            if application.current_stage != WorkflowStage.HANDOVER:
                return jsonify({"error": "Invalid stage for this action"}), 400

            application.status = RequestStatus.COMPLETED
            application.current_stage = WorkflowStage.HANDOVER
            completion_message = "Onboarding completed successfully!"
            response_message = "Onboarding completed successfully!"

        else:
            return jsonify({"error": "Invalid action"}), 400

        if next_stage:
            application.current_stage = next_stage

        application.updated_at = datetime.utcnow()

        response_message = response_message or completion_message

        timeline_events = [
            RequestTimeline(  # type: ignore
                app_id=request_id,
                stage=previous_stage,
                status="COMPLETED",
                message=completion_message,
                performed_by=user_email,
            )
        ]

        if next_stage:
            timeline_events.append(
                RequestTimeline(  # type: ignore
                    app_id=request_id,
                    stage=next_stage,
                    status="IN_PROGRESS",
                    message=next_stage_message
                    or f"{next_stage.value.replace('_', ' ').title()} started.",
                    performed_by=user_email,
                )
            )

        for event in timeline_events:
            db.session.add(event)

        db.session.commit()

        return jsonify(
            {
                "message": response_message,
                "current_stage": application.current_stage.value,
                "status": application.status.value,
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/requests/<int:request_id>/fail", methods=["POST"])
def fail_stage(request_id: int):
    """Mark a stage as failed (Admin only).

    Args:
        request_id: Application ID

    Returns:
        JSON with failure status
    """
    user_email = get_current_user_email()
    services = get_services()

    if not services["auth"].is_admin(user_email):
        return jsonify({"error": "Unauthorized - Admin access required"}), 403

    try:
        # TODO: Implement in ApplicationService as fail_workflow_stage()
        from app.models import Application, RequestTimeline

        data = request.json
        reason = data.get("reason", "No reason provided")

        application = Application.query.get_or_404(request_id)

        if not application.current_stage:
            return jsonify({"error": "No active stage to fail"}), 400

        # Mark stage as failed
        timeline = RequestTimeline(  # type: ignore
            app_id=request_id,
            stage=application.current_stage,
            status="FAILED",
            message=f"Stage failed: {reason}",
            performed_by=user_email,
        )
        db.session.add(timeline)

        application.status = RequestStatus.FAILED
        db.session.commit()

        return jsonify(
            {"message": "Stage marked as failed", "status": application.status.value}
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Lookup Data Endpoints
# ============================================================================


@api_bp.route("/lookup", methods=["GET"])
def get_lookup_data():
    """Get lookup data (Organizations, LOBs, Environments, etc.).

    Query Parameters:
        field: Optional filter by field type

    Returns:
        JSON dictionary grouped by field
    """
    services = get_services()
    field_type = request.args.get("field")

    try:
        if field_type:
            lookup_data = services["lookup"].get_lookup_by_field(field_type)
            result = {field_type: [item.to_dict() for item in lookup_data]}
        else:
            lookup_dict = services["lookup"].get_all_lookups()
            result = {
                field: [item.to_dict() for item in items]
                for field, items in lookup_dict.items()
            }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/lookup", methods=["POST"])
def create_lookup_data():
    """Create new lookup data (Admin only).

    Returns:
        JSON with created lookup ID
    """
    user_email = get_current_user_email()
    services = get_services()

    if not services["auth"].is_admin(user_email):
        return jsonify({"error": "Unauthorized - Admin access required"}), 403

    try:
        data = LookupDataCreate(**request.json)  # type: ignore

        # Create lookup using service
        lookup = services["lookup"].create_lookup(
            field=data.field, value=data.value, abbreviation=data.abbreviation
        )

        return (
            jsonify({"message": "Lookup data created successfully", "id": lookup.id}),
            201,
        )

    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Statistics & Audit Endpoints
# ============================================================================


@api_bp.route("/requests/<int:request_id>/comments", methods=["POST"])
def add_comment(request_id: int):
    """Add a comment to a request.

    Args:
        request_id: Application ID

    Returns:
        JSON with comment details
    """
    user_email = get_current_user_email()
    services = get_services()

    try:
        from app.models import Application, RequestComment

        application = Application.query.get_or_404(request_id)

        # Check authorization - requester or admin can comment
        if (
            not services["auth"].is_admin(user_email)
            and application.requested_by != user_email
        ):
            return jsonify({"error": "Unauthorized"}), 403

        comment_text = request.json.get("comment", "").strip()
        if not comment_text:
            return jsonify({"error": "Comment cannot be empty"}), 400

        comment = RequestComment(
            app_id=request_id, user_email=user_email, comment=comment_text
        )
        db.session.add(comment)
        db.session.commit()

        return (
            jsonify(
                {
                    "message": "Comment added successfully",
                    "comment": {
                        "id": comment.id,
                        "user_email": comment.user_email,
                        "comment": comment.comment,
                        "created_at": comment.created_at.isoformat(),
                    },
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/requests/<int:request_id>/cancel", methods=["POST"])
def cancel_request(request_id: int):
    """Cancel a request (DRAFT or PENDING only).

    Args:
        request_id: Application ID

    Returns:
        JSON with cancellation status
    """
    user_email = get_current_user_email()
    services = get_services()

    try:
        is_admin = services["auth"].is_admin(user_email)

        cancellation_reason = request.json.get("cancellation_reason", "").strip()
        if not cancellation_reason:
            return jsonify({"error": "Cancellation reason is required"}), 400

        application = services["app"].cancel_application(
            app_id=request_id,
            user_email=user_email,
            is_admin=is_admin,
            cancellation_reason=cancellation_reason,
            ip_address=request.remote_addr,
        )

        return (
            jsonify(
                {
                    "message": "Request cancelled successfully",
                    "status": application.status.value,
                    "current_stage": application.current_stage.value,
                }
            ),
            200,
        )

    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/requests/<int:request_id>/expedite", methods=["POST"])
def expedite_request(request_id: int):
    """Request expedite processing for a pending request.

    Args:
        request_id: Application ID

    Returns:
        JSON with expedite status
    """
    user_email = get_current_user_email()
    services = get_services()

    try:
        is_admin = services["auth"].is_admin(user_email)

        expedite_reason = request.json.get("expedite_reason", "").strip()
        if not expedite_reason:
            return jsonify({"error": "Expedite reason is required"}), 400

        application = services["app"].expedite_application(
            app_id=request_id,
            user_email=user_email,
            is_admin=is_admin,
            expedite_reason=expedite_reason,
            ip_address=request.remote_addr,
        )

        return (
            jsonify(
                {
                    "message": "Expedite request submitted successfully",
                    "expedite_requested": application.expedite_requested,
                    "expedite_requested_at": (
                        application.expedite_requested_at.isoformat()
                        if application.expedite_requested_at
                        else None
                    ),
                }
            ),
            200,
        )

    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/stats", methods=["GET"])
def get_stats():
    """Get dashboard statistics.

    Returns different stats for admin vs regular users.

    Returns:
        JSON with statistics
    """
    user_email = get_current_user_email()
    services = get_services()

    try:
        if services["auth"].is_admin(user_email):
            stats = services["app"].get_dashboard_stats()
        else:
            from app.repositories import ApplicationRepository

            app_repo = ApplicationRepository(db)
            stats = {
                "my_requests": app_repo.count_by_requester(user_email),
                "pending": len(
                    [
                        app
                        for app in app_repo.get_by_requester(user_email)
                        if app.status == RequestStatus.PENDING
                    ]
                ),
                "approved": len(
                    [
                        app
                        for app in app_repo.get_by_requester(user_email)
                        if app.status == RequestStatus.APPROVED
                    ]
                ),
            }

        return jsonify(stats)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/audit", methods=["GET"])
def get_audit_log():
    """Get audit log (Admin only).

    Query Parameters:
        limit: Maximum number of records (default: 100)

    Returns:
        JSON with audit log entries
    """
    user_email = get_current_user_email()
    services = get_services()

    if not services["auth"].is_admin(user_email):
        return jsonify({"error": "Unauthorized - Admin access required"}), 403

    try:
        limit = request.args.get("limit", 100, type=int)

        audit_repo = AuditRepository(db)
        audits = audit_repo.get_recent(limit)

        return jsonify({"audits": [audit.to_dict() for audit in audits]})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
