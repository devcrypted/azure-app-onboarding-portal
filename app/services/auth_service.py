"""Authentication service - business logic for authentication and authorization."""

from __future__ import annotations

from typing import Optional

from flask import session

from app.core import get_settings


class AuthService:
    """Service for authentication and authorization logic."""

    def __init__(self) -> None:
        """Initialize auth service."""
        self.settings = get_settings()

    def is_authenticated(self) -> bool:
        """Check if user is authenticated.

        Returns:
            True if user is authenticated
        """
        return session.get("user") is not None

    def is_admin(self, user_email: Optional[str] = None) -> bool:
        """Check if user has admin privileges.

        Args:
            user_email: Email to check (defaults to current session user)

        Returns:
            True if user is admin
        """
        if user_email is None:
            user_email = self.get_current_user_email()

        if not user_email:
            return False

        return user_email.lower() in [
            email.lower() for email in self.settings.admin_emails
        ]

    def is_network_admin(self, user_email: Optional[str] = None) -> bool:
        """Check if user has network admin privileges."""

        if user_email is None:
            user_email = self.get_current_user_email()

        if not user_email:
            return False

        return user_email.lower() in [
            email.lower() for email in self.settings.network_admin_emails
        ]

    def get_current_user(self) -> Optional[dict]:
        """Get current authenticated user from session.

        Returns:
            User dict or None
        """
        return session.get("user")

    def get_current_user_email(self) -> Optional[str]:
        """Get current user's email.

        Returns:
            User email or None
        """
        user = self.get_current_user()
        return user.get("email") if user else None

    def login_user(self, user_data: dict) -> None:
        """Log in a user by storing in session.

        Args:
            user_data: Dictionary with user information (email, name, etc.)
        """
        session["user"] = user_data
        session.permanent = True

    def logout_user(self) -> None:
        """Log out current user by clearing session."""
        session.clear()

    def require_authentication(self) -> bool:
        """Check if authentication is required.

        Returns:
            True if user must be authenticated
        """
        if not self.is_authenticated():
            return True
        return False

    def require_admin(self) -> bool:
        """Check if admin privileges are required.

        Returns:
            True if user must be admin
        """
        if not self.is_admin():
            return True
        return False

    def get_oauth_enabled(self) -> bool:
        """Check if OAuth is enabled.

        Returns:
            True if OAuth is configured and enabled
        """
        return bool(self.settings.oauth.authority and self.settings.oauth.client_id)

    def get_oauth_authority(self) -> Optional[str]:
        """Get OAuth authority URL.

        Returns:
            OAuth authority URL or None
        """
        return self.settings.oauth.authority

    def get_oauth_client_id(self) -> Optional[str]:
        """Get OAuth client ID.

        Returns:
            OAuth client ID or None
        """
        return self.settings.oauth.client_id

    def get_oauth_redirect_uri(self) -> Optional[str]:
        """Get OAuth redirect URI.

        Returns:
            OAuth redirect URI or None
        """
        return self.settings.oauth.redirect_uri

    def get_oauth_scopes(self) -> list:
        """Get OAuth scopes.

        Returns:
            List of OAuth scopes
        """
        return self.settings.oauth.scopes
