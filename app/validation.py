"""Validation schemas for TradeX Platform Onboarding."""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
import re
import ipaddress


class EnvironmentCreate(BaseModel):
    """Schema for environment creation."""

    environment_name: str = Field(
        ..., min_length=1, max_length=50, description="Environment name"
    )
    region: str = Field(..., min_length=1, max_length=50, description="Azure region")

    @field_validator("environment_name")
    @classmethod
    def validate_environment_name(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Environment name cannot be empty")
        return v.strip()

    @field_validator("region")
    @classmethod
    def validate_region(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Region cannot be empty")
        return v.strip()


class ApplicationCreate(BaseModel):
    """Schema for application creation (onboarding request)."""

    app_slug: str = Field(
        ..., min_length=4, max_length=6, description="Application slug (4-6 characters)"
    )
    application_name: str = Field(
        ..., min_length=3, max_length=200, description="Application name"
    )
    organization: str = Field(
        ..., min_length=1, max_length=100, description="Organization"
    )
    lob: str = Field(..., min_length=1, max_length=100, description="Line of Business")
    platform: str = Field(default="Azure", max_length=50, description="Platform")
    environments: List[EnvironmentCreate] = Field(
        ..., min_items=1, description="At least one environment required"
    )

    @field_validator("app_slug")
    @classmethod
    def validate_app_slug(cls, v):
        if not v or v.strip() == "":
            raise ValueError("App slug cannot be empty")

        v = v.strip().lower()

        if len(v) < 4:
            raise ValueError("App slug must be at least 4 characters long")

        if len(v) > 6:
            raise ValueError("App slug must be at most 6 characters long")

        # Only alphanumeric lowercase characters allowed
        if not re.match(r"^[a-z0-9]+$", v):
            raise ValueError(
                "App slug must contain only lowercase letters and numbers (no spaces or special characters)"
            )

        return v

    @field_validator("application_name")
    @classmethod
    def validate_application_name(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Application name cannot be empty")

        if len(v.strip()) < 3:
            raise ValueError("Application name must be at least 3 characters long")

        return v.strip()

    @field_validator("organization")
    @classmethod
    def validate_organization(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Organization cannot be empty")
        return v.strip()

    @field_validator("lob")
    @classmethod
    def validate_lob(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Line of Business cannot be empty")
        return v.strip()

    @field_validator("environments")
    @classmethod
    def validate_environments(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one environment is required")

        # Check for duplicate environment names
        env_names = [env.environment_name.lower() for env in v]
        if len(env_names) != len(set(env_names)):
            raise ValueError("Duplicate environment names are not allowed")

        return v


class ApplicationUpdate(BaseModel):
    """Schema for application update."""

    application_name: Optional[str] = Field(None, min_length=3, max_length=200)
    organization: Optional[str] = Field(None, min_length=1, max_length=100)
    lob: Optional[str] = Field(None, min_length=1, max_length=100)
    platform: Optional[str] = Field(None, max_length=50)
    environments: Optional[List[EnvironmentCreate]] = Field(None, min_items=1)

    @field_validator("application_name")
    @classmethod
    def validate_application_name(cls, v):
        if v is not None and (not v or v.strip() == ""):
            raise ValueError("Application name cannot be empty")
        return v.strip() if v else v

    @field_validator("organization")
    @classmethod
    def validate_organization(cls, v):
        if v is not None and (not v or v.strip() == ""):
            raise ValueError("Organization cannot be empty")
        return v.strip() if v else v

    @field_validator("lob")
    @classmethod
    def validate_lob(cls, v):
        if v is not None and (not v or v.strip() == ""):
            raise ValueError("Line of Business cannot be empty")
        return v.strip() if v else v


class SubscriptionAssignment(BaseModel):
    """Schema for subscription assignment."""

    environment_id: int = Field(..., description="Environment ID")
    subscription_id: str = Field(
        ..., min_length=36, max_length=36, description="Azure Subscription ID (GUID)"
    )

    @field_validator("subscription_id")
    @classmethod
    def validate_subscription_id(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Subscription ID cannot be empty")

        v = v.strip()

        # Validate GUID format
        guid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        if not re.match(guid_pattern, v.lower()):
            raise ValueError(
                "Subscription ID must be a valid GUID format (e.g., 12345678-1234-1234-1234-123456789abc)"
            )

        return v


class CommentCreate(BaseModel):
    """Schema for comment creation."""

    comment: str = Field(..., min_length=1, max_length=5000, description="Comment text")
    is_internal: bool = Field(
        default=False, description="Internal comment (admin only)"
    )

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Comment cannot be empty")
        return v.strip()


class StageUpdate(BaseModel):
    """Schema for stage update."""

    stage: str = Field(..., description="New stage")
    message: Optional[str] = Field(
        None, max_length=1000, description="Stage update message"
    )

    @field_validator("stage")
    @classmethod
    def validate_stage(cls, v):
        valid_stages = [
            "SUBSCRIPTION_ASSIGNMENT",
            "FOUNDATION_INFRA",
            "INFRASTRUCTURE",
            "HANDOVER",
        ]
        if v not in valid_stages:
            raise ValueError(
                f"Invalid stage. Must be one of: {', '.join(valid_stages)}"
            )
        return v


class FirewallRequestCreate(BaseModel):
    """Schema for firewall rule request creation."""

    application_name: str = Field(
        ..., min_length=3, max_length=200, description="Application name"
    )
    source_ip_ranges: List[str] = Field(
        ..., min_items=1, description="Source IP ranges or CIDR blocks"
    )
    destination_ip_ranges: List[str] = Field(
        ..., min_items=1, description="Destination IP ranges or CIDR blocks"
    )
    ports: List[str] = Field(..., min_items=1, description="Port numbers or ranges")
    protocols: List[str] = Field(
        ..., min_items=1, description="Protocols (TCP, UDP, ICMP, etc.)"
    )
    justification: str = Field(
        ..., min_length=10, max_length=2000, description="Business justification"
    )

    @field_validator("application_name")
    @classmethod
    def validate_application_name(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Application name cannot be empty")
        if len(v.strip()) < 3:
            raise ValueError("Application name must be at least 3 characters long")
        return v.strip()

    @field_validator("source_ip_ranges", "destination_ip_ranges")
    @classmethod
    def validate_ip_ranges(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one IP range is required")

        for ip_range in v:
            ip_range = ip_range.strip()
            if not ip_range:
                raise ValueError("IP range cannot be empty")

            # Check if it's a valid IP address or CIDR block
            try:
                # Try parsing as network (CIDR)
                ipaddress.ip_network(ip_range, strict=False)
            except ValueError:
                # Try parsing as single IP address
                try:
                    ipaddress.ip_address(ip_range)
                except ValueError:
                    raise ValueError(
                        f"'{ip_range}' is not a valid IP address or CIDR block"
                    )

        return [ip.strip() for ip in v]

    @field_validator("ports")
    @classmethod
    def validate_ports(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one port is required")

        for port in v:
            port_str = str(port).strip()
            if not port_str:
                raise ValueError("Port cannot be empty")

            # Check if it's a port range (e.g., "80-443") or single port
            if "-" in port_str:
                try:
                    start, end = port_str.split("-")
                    start_port = int(start.strip())
                    end_port = int(end.strip())
                    if not (1 <= start_port <= 65535 and 1 <= end_port <= 65535):
                        raise ValueError(
                            f"Port range '{port_str}' contains invalid port numbers (must be 1-65535)"
                        )
                    if start_port >= end_port:
                        raise ValueError(
                            f"Port range '{port_str}' start must be less than end"
                        )
                except ValueError as e:
                    if "invalid literal" in str(e):
                        raise ValueError(f"Port range '{port_str}' is not valid")
                    raise
            else:
                # Single port
                try:
                    port_num = int(port_str)
                    if not (1 <= port_num <= 65535):
                        raise ValueError(
                            f"Port '{port_str}' must be between 1 and 65535"
                        )
                except ValueError:
                    raise ValueError(f"Port '{port_str}' is not a valid number")

        return [str(p).strip() for p in v]

    @field_validator("protocols")
    @classmethod
    def validate_protocols(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one protocol is required")

        valid_protocols = ["TCP", "UDP", "ICMP", "ESP", "AH", "GRE", "ANY"]
        for protocol in v:
            protocol_upper = protocol.strip().upper()
            if protocol_upper not in valid_protocols:
                raise ValueError(
                    f"Protocol '{protocol}' is not valid. Must be one of: {', '.join(valid_protocols)}"
                )

        return [p.strip().upper() for p in v]

    @field_validator("justification")
    @classmethod
    def validate_justification(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Justification cannot be empty")
        if len(v.strip()) < 10:
            raise ValueError("Justification must be at least 10 characters long")
        return v.strip()


class SubscriptionManagementCreate(BaseModel):
    """Schema for subscription management request creation."""

    subscription_name: str = Field(
        ..., min_length=3, max_length=200, description="Subscription name"
    )
    subscription_id: str = Field(
        ..., min_length=36, max_length=36, description="Azure Subscription ID (GUID)"
    )
    owner_emails: List[str] = Field(
        ..., min_items=1, description="Owner email addresses"
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Subscription description"
    )

    @field_validator("subscription_name")
    @classmethod
    def validate_subscription_name(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Subscription name cannot be empty")
        if len(v.strip()) < 3:
            raise ValueError("Subscription name must be at least 3 characters long")
        return v.strip()

    @field_validator("subscription_id")
    @classmethod
    def validate_subscription_id(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Subscription ID cannot be empty")

        v = v.strip()

        # Validate GUID format
        guid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        if not re.match(guid_pattern, v.lower()):
            raise ValueError(
                "Subscription ID must be a valid GUID format (e.g., 12345678-1234-1234-1234-123456789abc)"
            )

        return v

    @field_validator("owner_emails")
    @classmethod
    def validate_owner_emails(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one owner email is required")

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        for email in v:
            email_stripped = email.strip()
            if not email_stripped:
                raise ValueError("Owner email cannot be empty")
            if not re.match(email_pattern, email_stripped):
                raise ValueError(f"'{email}' is not a valid email address")

        # Check for duplicates
        emails_lower = [e.strip().lower() for e in v]
        if len(emails_lower) != len(set(emails_lower)):
            raise ValueError("Duplicate owner emails are not allowed")

        return [e.strip() for e in v]

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        if v is not None and v.strip() == "":
            return None  # Convert empty string to None
        return v.strip() if v else v


class OrganizationCreate(BaseModel):
    """Schema for organization creation request."""

    organization_name: str = Field(
        ..., min_length=2, max_length=100, description="Organization name"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Organization description"
    )

    @field_validator("organization_name")
    @classmethod
    def validate_organization_name(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Organization name cannot be empty")
        if len(v.strip()) < 2:
            raise ValueError("Organization name must be at least 2 characters long")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        if v is not None and v.strip() == "":
            return None
        return v.strip() if v else v


class LOBCreate(BaseModel):
    """Schema for Line of Business creation request."""

    lob_name: str = Field(
        ..., min_length=2, max_length=100, description="Line of Business name"
    )
    organization: str = Field(
        ..., min_length=1, max_length=100, description="Parent organization"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="LOB description"
    )

    @field_validator("lob_name")
    @classmethod
    def validate_lob_name(cls, v):
        if not v or v.strip() == "":
            raise ValueError("LOB name cannot be empty")
        if len(v.strip()) < 2:
            raise ValueError("LOB name must be at least 2 characters long")
        return v.strip()

    @field_validator("organization")
    @classmethod
    def validate_organization(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Organization cannot be empty")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        if v is not None and v.strip() == "":
            return None
        return v.strip() if v else v
