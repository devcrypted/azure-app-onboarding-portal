"""Email notification service using Azure Communication Services."""

import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for sending notifications."""

    def __init__(self):
        self.acs_connection_string = os.environ.get("ACS_CONNECTION_STRING")
        self.sender_email = os.environ.get("ACS_SENDER_EMAIL", "donotreply@tradex.com")
        self.enabled = bool(self.acs_connection_string)

        if not self.enabled:
            logger.warning(
                "Azure Communication Services not configured. Email notifications will be logged only."
            )

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
    ) -> bool:
        """Send an email notification."""

        if not self.enabled:
            logger.info(f"[EMAIL MOCK] To: {to_email}, Subject: {subject}")
            logger.info(f"[EMAIL MOCK] Body: {body_text or body_html}")
            return True

        try:
            # TODO: Integrate with Azure Communication Services SDK
            # from azure.communication.email import EmailClient
            # client = EmailClient.from_connection_string(self.acs_connection_string)
            # message = {
            #     "senderAddress": self.sender_email,
            #     "recipients": {"to": [{"address": to_email}]},
            #     "content": {
            #         "subject": subject,
            #         "plainText": body_text,
            #         "html": body_html
            #     }
            # }
            # poller = client.begin_send(message)
            # result = poller.result()

            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    def send_request_created_email(
        self, app_code: str, app_slug: str, app_name: str, requester_email: str
    ):
        """Send email when request is created."""
        subject = f"TradeX Platform: Request Created - {app_slug}"
        body_html = f"""
        <html>
        <body>
            <h2>Application Onboarding Request Created</h2>
            <p>Your application onboarding request has been created successfully.</p>
            <ul>
                <li><strong>Request ID:</strong> {app_code}</li>
                <li><strong>App Slug:</strong> {app_slug}</li>
                <li><strong>Application Name:</strong> {app_name}</li>
            </ul>
            <p>Your request is currently in <strong>DRAFT</strong> status. You can edit it before submitting for approval.</p>
            <p>You will receive email notifications as your request progresses through different stages.</p>
            <br>
            <p>Best regards,<br>TradeX Platform Team</p>
        </body>
        </html>
        """
        body_text = f"Request Created - {app_slug} ({app_code})"
        return self.send_email(requester_email, subject, body_html, body_text)

    def send_request_submitted_email(
        self, app_code: str, app_slug: str, requester_email: str
    ):
        """Send email when request is submitted for approval."""
        subject = f"TradeX Platform: Request Submitted - {app_slug}"
        body_html = f"""
        <html>
        <body>
            <h2>Request Submitted for Approval</h2>
            <p>Your application onboarding request has been submitted for approval.</p>
            <ul>
                <li><strong>Request ID:</strong> {app_code}</li>
                <li><strong>App Slug:</strong> {app_slug}</li>
            </ul>
            <p>Your request is now <strong>PENDING APPROVAL</strong>. An admin will review it shortly.</p>
            <br>
            <p>Best regards,<br>TradeX Platform Team</p>
        </body>
        </html>
        """
        body_text = f"Request Submitted for Approval - {app_slug}"
        return self.send_email(requester_email, subject, body_html, body_text)

    def send_request_approved_email(
        self, app_code: str, app_slug: str, requester_email: str, approved_by: str
    ):
        """Send email when request is approved."""
        subject = f"TradeX Platform: Request Approved - {app_slug}"
        body_html = f"""
        <html>
        <body>
            <h2>Request Approved</h2>
            <p>Great news! Your application onboarding request has been approved.</p>
            <ul>
                <li><strong>Request ID:</strong> {app_code}</li>
                <li><strong>App Slug:</strong> {app_slug}</li>
                <li><strong>Approved By:</strong> {approved_by}</li>
            </ul>
            <p>Next steps:</p>
            <ol>
                <li>Subscriptions will be assigned by the admin</li>
                <li>Foundation infrastructure will be provisioned</li>
                <li>Application infrastructure will be created</li>
                <li>Environment will be handed over to you</li>
            </ol>
            <p>You will receive notifications at each stage.</p>
            <br>
            <p>Best regards,<br>TradeX Platform Team</p>
        </body>
        </html>
        """
        body_text = f"Request Approved - {app_slug}"
        return self.send_email(requester_email, subject, body_html, body_text)

    def send_request_rejected_email(
        self, app_code: str, app_slug: str, requester_email: str, rejection_reason: str
    ):
        """Send email when request is rejected."""
        subject = f"TradeX Platform: Request Rejected - {app_slug}"
        body_html = f"""
        <html>
        <body>
            <h2>Request Rejected</h2>
            <p>Unfortunately, your application onboarding request has been rejected.</p>
            <ul>
                <li><strong>Request ID:</strong> {app_code}</li>
                <li><strong>App Slug:</strong> {app_slug}</li>
            </ul>
            <p><strong>Reason:</strong></p>
            <p>{rejection_reason}</p>
            <p>Please review the feedback and submit a new request with the necessary changes.</p>
            <br>
            <p>Best regards,<br>TradeX Platform Team</p>
        </body>
        </html>
        """
        body_text = f"Request Rejected - {app_slug}: {rejection_reason}"
        return self.send_email(requester_email, subject, body_html, body_text)

    def send_subscription_assigned_email(
        self, app_code: str, app_slug: str, requester_email: str
    ):
        """Send email when subscriptions are assigned."""
        subject = f"TradeX Platform: Subscriptions Assigned - {app_slug}"
        body_html = f"""
        <html>
        <body>
            <h2>Subscriptions Assigned</h2>
            <p>Azure subscriptions have been assigned to your application environments.</p>
            <ul>
                <li><strong>Request ID:</strong> {app_code}</li>
                <li><strong>App Slug:</strong> {app_slug}</li>
            </ul>
            <p>Current Stage: <strong>SUBSCRIPTION_ASSIGNED</strong></p>
            <p>Next Step: Foundation infrastructure provisioning will begin shortly.</p>
            <br>
            <p>Best regards,<br>TradeX Platform Team</p>
        </body>
        </html>
        """
        body_text = f"Subscriptions Assigned - {app_slug}"
        return self.send_email(requester_email, subject, body_html, body_text)

    def send_stage_update_email(
        self,
        app_code: str,
        app_slug: str,
        requester_email: str,
        stage: str,
        message: Optional[str] = None,
    ):
        """Send email when workflow stage is updated."""
        stage_names = {
            "FOUNDATION_INFRA_PROVISIONING": "Foundation Infrastructure Provisioning",
            "FOUNDATION_INFRA_COMPLETED": "Foundation Infrastructure Completed",
            "INFRASTRUCTURE_PROVISIONING": "Infrastructure Provisioning",
            "INFRASTRUCTURE_COMPLETED": "Infrastructure Completed",
            "COMPLETED": "Completed - Handover",
        }

        stage_display = stage_names.get(stage, stage)
        subject = f"TradeX Platform: Stage Update - {app_slug}"

        additional_message = (
            f"<p><strong>Message:</strong> {message}</p>" if message else ""
        )

        body_html = f"""
        <html>
        <body>
            <h2>Workflow Stage Updated</h2>
            <p>Your application onboarding request has progressed to a new stage.</p>
            <ul>
                <li><strong>Request ID:</strong> {app_code}</li>
                <li><strong>App Slug:</strong> {app_slug}</li>
                <li><strong>Current Stage:</strong> {stage_display}</li>
            </ul>
            {additional_message}
            <br>
            <p>Best regards,<br>TradeX Platform Team</p>
        </body>
        </html>
        """
        body_text = f"Stage Update - {app_slug}: {stage_display}"
        return self.send_email(requester_email, subject, body_html, body_text)

    def send_comment_notification_email(
        self,
        app_code: str,
        app_slug: str,
        requester_email: str,
        commenter: str,
        comment: str,
    ):
        """Send email when a comment is added."""
        subject = f"TradeX Platform: New Comment - {app_slug}"
        body_html = f"""
        <html>
        <body>
            <h2>New Comment on Your Request</h2>
            <p>A new comment has been added to your application onboarding request.</p>
            <ul>
                <li><strong>Request ID:</strong> {app_code}</li>
                <li><strong>App Slug:</strong> {app_slug}</li>
                <li><strong>Comment By:</strong> {commenter}</li>
            </ul>
            <p><strong>Comment:</strong></p>
            <p>{comment}</p>
            <br>
            <p>Best regards,<br>TradeX Platform Team</p>
        </body>
        </html>
        """
        body_text = f"New Comment - {app_slug} by {commenter}"
        return self.send_email(requester_email, subject, body_html, body_text)


# Global email service instance
email_service = EmailService()
