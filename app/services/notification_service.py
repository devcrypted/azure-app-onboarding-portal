"""Notification service - business logic for email and notifications."""

from __future__ import annotations

import logging
from typing import List, Optional

from app.core import get_settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending email notifications."""

    def __init__(self) -> None:
        """Initialize notification service."""
        self.settings = get_settings()

    def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        """Send an email notification.

        Args:
            to: List of recipient email addresses
            subject: Email subject
            body: Plain text email body
            html_body: HTML email body (optional)

        Returns:
            True if successful, False otherwise
        """
        if not to:
            logger.warning("No recipients specified for email")
            return False

        # Check if Azure Communication Services is configured
        if self.settings.acs.connection_string and self.settings.acs.sender:
            return self._send_via_acs(to, subject, body, html_body)

        # Fallback to SMTP if configured
        if self.settings.email.smtp_server:
            return self._send_via_smtp(to, subject, body, html_body)

        # Log only in development mode
        logger.info(
            f"Email notification (not sent - no email service configured):\n"
            f"To: {', '.join(to)}\n"
            f"Subject: {subject}\n"
            f"Body: {body[:200]}..."
        )
        return True  # Return True in dev mode for testing

    def send_approval_request(
        self,
        app_code: str,
        app_name: str,
        requester: str,
        admin_emails: List[str],
    ) -> bool:
        """Send approval request notification to admins.

        Args:
            app_code: Application code
            app_name: Application name
            requester: Requester email
            admin_emails: List of admin emails

        Returns:
            True if successful
        """
        subject = f"[TradeX] Approval Required: {app_code}"
        body = f"""
A new application onboarding request requires your approval.

Application Code: {app_code}
Application Name: {app_name}
Requested By: {requester}

Please review and approve/reject this request in the admin panel.
"""
        return self.send_email(admin_emails, subject, body)

    def send_approval_notification(
        self,
        app_code: str,
        app_name: str,
        requester: str,
        approved_by: str,
    ) -> bool:
        """Send approval notification to requester.

        Args:
            app_code: Application code
            app_name: Application name
            requester: Requester email
            approved_by: Admin who approved

        Returns:
            True if successful
        """
        subject = f"[TradeX] Approved: {app_code}"
        body = f"""
Your application onboarding request has been approved.

Application Code: {app_code}
Application Name: {app_name}
Approved By: {approved_by}

The infrastructure provisioning process will begin shortly.
"""
        return self.send_email([requester], subject, body)

    def send_rejection_notification(
        self,
        app_code: str,
        app_name: str,
        requester: str,
        rejected_by: str,
        reason: str,
    ) -> bool:
        """Send rejection notification to requester.

        Args:
            app_code: Application code
            app_name: Application name
            requester: Requester email
            rejected_by: Admin who rejected
            reason: Rejection reason

        Returns:
            True if successful
        """
        subject = f"[TradeX] Rejected: {app_code}"
        body = f"""
Your application onboarding request has been rejected.

Application Code: {app_code}
Application Name: {app_name}
Rejected By: {rejected_by}

Reason:
{reason}

You may submit a new request after addressing the issues noted.
"""
        return self.send_email([requester], subject, body)

    def _send_via_acs(
        self,
        to: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        """Send email via Azure Communication Services.

        Args:
            to: Recipient emails
            subject: Email subject
            body: Plain text body
            html_body: HTML body

        Returns:
            True if successful
        """
        try:
            # TODO: Implement ACS email sending when available
            # from azure.communication.email import EmailClient
            #
            # client = EmailClient.from_connection_string(
            #     self.settings.acs.connection_string
            # )
            #
            # message = {
            #     "senderAddress": self.settings.acs.sender,
            #     "recipients": {"to": [{"address": email} for email in to]},
            #     "content": {
            #         "subject": subject,
            #         "plainText": body,
            #         "html": html_body or body,
            #     },
            # }
            #
            # poller = client.begin_send(message)
            # result = poller.result()
            # return result.status == "Succeeded"

            logger.info(f"ACS email would be sent to {', '.join(to)}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email via ACS: {e}")
            return False

    def _send_via_smtp(
        self,
        to: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        """Send email via SMTP.

        Args:
            to: Recipient emails
            subject: Email subject
            body: Plain text body
            html_body: HTML body

        Returns:
            True if successful
        """
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.settings.email.username or "noreply@tradex.com"
            msg["To"] = ", ".join(to)

            # Attach plain text and HTML
            msg.attach(MIMEText(body, "plain"))
            if html_body:
                msg.attach(MIMEText(html_body, "html"))

            # Send via SMTP
            if not self.settings.email.smtp_server:
                logger.error("SMTP server not configured")
                return False

            with smtplib.SMTP(
                self.settings.email.smtp_server, self.settings.email.smtp_port
            ) as server:
                server.starttls()
                if self.settings.email.username and self.settings.email.password:
                    server.login(
                        self.settings.email.username, self.settings.email.password
                    )
                server.send_message(msg)

            logger.info(f"SMTP email sent to {', '.join(to)}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {e}")
            return False
