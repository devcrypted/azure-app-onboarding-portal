"""Audit repository for database operations on audit and timeline models."""

from __future__ import annotations

from typing import List, Optional

from flask_sqlalchemy import SQLAlchemy

from app.models import RequestAudit, RequestComment, RequestTimeline, WorkflowStage
from app.repositories.base_repository import BaseRepository


class AuditRepository(BaseRepository[RequestAudit]):
    """Repository for RequestAudit entity operations."""

    def __init__(self, db: SQLAlchemy) -> None:
        """Initialize audit repository.

        Args:
            db: SQLAlchemy database instance
        """
        super().__init__(db, RequestAudit)

    def get_by_app_id(
        self, app_id: int, skip: int = 0, limit: int = 100
    ) -> List[RequestAudit]:
        """Get audit logs for a specific application.

        Args:
            app_id: Application ID
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of audit records
        """
        return (
            self.query()
            .filter_by(app_id=app_id)
            .order_by(RequestAudit.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_user(
        self, user_email: str, skip: int = 0, limit: int = 100
    ) -> List[RequestAudit]:
        """Get audit logs for a specific user.

        Args:
            user_email: User email address
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of audit records
        """
        return (
            self.query()
            .filter_by(user_email=user_email)
            .order_by(RequestAudit.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_request_type(
        self, request_type: str, skip: int = 0, limit: int = 100
    ) -> List[RequestAudit]:
        """Get audit logs by request type.

        Args:
            request_type: Request type (CREATE, UPDATE, DELETE, APPROVE, etc.)
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of audit records
        """
        return (
            self.query()
            .filter_by(request_type=request_type)
            .order_by(RequestAudit.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_recent(self, limit: int = 50) -> List[RequestAudit]:
        """Get most recent audit logs.

        Args:
            limit: Maximum records to return

        Returns:
            List of recent audit records
        """
        return self.query().order_by(RequestAudit.timestamp.desc()).limit(limit).all()


class CommentRepository(BaseRepository[RequestComment]):
    """Repository for RequestComment entity operations."""

    def __init__(self, db: SQLAlchemy) -> None:
        """Initialize comment repository.

        Args:
            db: SQLAlchemy database instance
        """
        super().__init__(db, RequestComment)

    def get_by_app_id(
        self,
        app_id: int,
        include_internal: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[RequestComment]:
        """Get comments for a specific application.

        Args:
            app_id: Application ID
            include_internal: Include admin-only internal comments
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of comments
        """
        query = self.query().filter_by(app_id=app_id)

        if not include_internal:
            query = query.filter_by(is_internal=False)

        return (
            query.order_by(RequestComment.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_user(
        self, user_email: str, skip: int = 0, limit: int = 100
    ) -> List[RequestComment]:
        """Get comments by a specific user.

        Args:
            user_email: User email address
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of comments
        """
        return (
            self.query()
            .filter_by(user_email=user_email)
            .order_by(RequestComment.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_by_app_id(self, app_id: int, include_internal: bool = True) -> int:
        """Count comments for an application.

        Args:
            app_id: Application ID
            include_internal: Include admin-only internal comments

        Returns:
            Count of comments
        """
        query = self.query().filter_by(app_id=app_id)

        if not include_internal:
            query = query.filter_by(is_internal=False)

        return query.count()


class TimelineRepository(BaseRepository[RequestTimeline]):
    """Repository for RequestTimeline entity operations."""

    def __init__(self, db: SQLAlchemy) -> None:
        """Initialize timeline repository.

        Args:
            db: SQLAlchemy database instance
        """
        super().__init__(db, RequestTimeline)

    def get_by_app_id(self, app_id: int) -> List[RequestTimeline]:
        """Get timeline events for a specific application.

        Args:
            app_id: Application ID

        Returns:
            List of timeline events ordered chronologically
        """
        return (
            self.query()
            .filter_by(app_id=app_id)
            .order_by(RequestTimeline.created_at.asc())
            .all()
        )

    def get_by_stage(self, app_id: int, stage: WorkflowStage) -> List[RequestTimeline]:
        """Get timeline events for a specific stage.

        Args:
            app_id: Application ID
            stage: Workflow stage enum

        Returns:
            List of timeline events for the stage
        """
        return (
            self.query()
            .filter_by(app_id=app_id, stage=stage)
            .order_by(RequestTimeline.created_at.asc())
            .all()
        )

    def get_latest_event(self, app_id: int) -> Optional[RequestTimeline]:
        """Get the most recent timeline event for an application.

        Args:
            app_id: Application ID

        Returns:
            Latest timeline event or None
        """
        return (
            self.query()
            .filter_by(app_id=app_id)
            .order_by(RequestTimeline.created_at.desc())
            .first()
        )

    def get_completed_stages(self, app_id: int) -> List[WorkflowStage]:
        """Get list of completed workflow stages for an application.

        Args:
            app_id: Application ID

        Returns:
            List of completed workflow stages
        """
        events = (
            self.query()
            .filter_by(app_id=app_id, status="COMPLETED")
            .order_by(RequestTimeline.created_at.asc())
            .all()
        )
        return [event.stage for event in events]
