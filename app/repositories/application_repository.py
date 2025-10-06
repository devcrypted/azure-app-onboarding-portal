"""Application repository for database operations on Application model."""

from __future__ import annotations

from typing import List, Optional

from flask_sqlalchemy import SQLAlchemy

from app.models import (
    Application,
    RequestStatus,
    RequestType,
)
from app.repositories.base_repository import BaseRepository


class ApplicationRepository(BaseRepository[Application]):
    """Repository for Application entity operations."""

    def __init__(self, db: SQLAlchemy) -> None:
        """Initialize application repository.

        Args:
            db: SQLAlchemy database instance
        """
        super().__init__(db, Application)

    def get_by_app_code(self, app_code: str) -> Optional[Application]:
        """Get application by app code.

        Args:
            app_code: Unique application code (e.g., APP-00001)

        Returns:
            Application instance or None
        """
        return self.get_one_by_filter(app_code=app_code)

    def get_by_app_slug(self, app_slug: str) -> Optional[Application]:
        """Get application by slug.

        Args:
            app_slug: User-defined slug (4-6 characters)

        Returns:
            Application instance or None
        """
        return self.get_one_by_filter(app_slug=app_slug)

    def get_by_requester(
        self, requested_by: str, skip: int = 0, limit: int = 100
    ) -> List[Application]:
        """Get applications created by a specific user.

        Args:
            requested_by: User email address
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of applications
        """
        return (
            self.query()
            .filter_by(requested_by=requested_by)
            .order_by(Application.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_status(
        self, status: RequestStatus, skip: int = 0, limit: int = 100
    ) -> List[Application]:
        """Get applications by status.

        Args:
            status: Request status enum
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of applications
        """
        return (
            self.query()
            .filter_by(status=status)
            .order_by(Application.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_type(
        self, request_type: RequestType, skip: int = 0, limit: int = 100
    ) -> List[Application]:
        """Get applications by request type.

        Args:
            request_type: Request type enum
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of applications
        """
        return (
            self.query()
            .filter_by(request_type=request_type)
            .order_by(Application.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_pending_approvals(
        self, skip: int = 0, limit: int = 100
    ) -> List[Application]:
        """Get applications pending approval.

        Args:
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of pending applications
        """
        return self.get_by_status(RequestStatus.PENDING, skip, limit)

    def is_slug_available(self, app_slug: str) -> bool:
        """Check if app slug is available.

        Args:
            app_slug: Slug to check

        Returns:
            True if available, False if taken
        """
        return self.get_by_app_slug(app_slug) is None

    def get_latest_by_type(self, request_type: RequestType) -> Optional[Application]:
        """Get the most recent application of a given type.

        Args:
            request_type: Request type enum

        Returns:
            Latest application or None
        """
        return (
            self.query()
            .filter_by(request_type=request_type)
            .order_by(Application.id.desc())
            .first()
        )

    def count_by_status(self, status: RequestStatus) -> int:
        """Count applications by status.

        Args:
            status: Request status enum

        Returns:
            Count of applications
        """
        return self.query().filter_by(status=status).count()

    def count_by_requester(self, requested_by: str) -> int:
        """Count applications by requester.

        Args:
            requested_by: User email address

        Returns:
            Count of applications
        """
        return self.query().filter_by(requested_by=requested_by).count()
