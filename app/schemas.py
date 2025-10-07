"""Pydantic schemas for request validation."""

import ipaddress
import re
from datetime import date
from typing import List, Optional, Set
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

HOSTNAME_REGEX = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.?$"
)
PROTOCOL_OPTIONS = {"TCP", "UDP", "ICMP", "ESP", "AH", "GRE", "ANY"}
DIRECTION_OPTIONS = {"INBOUND", "OUTBOUND", "BIDIRECTIONAL"}
ENVIRONMENT_SCOPE_OPTIONS = {
    "DEV",
    "TEST",
    "QA",
    "STAGE",
    "UAT",
    "PROD",
    "DR",
}


def _normalise_endpoint(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Value cannot be empty")

    wildcard_values = {"*", "any", "ANY"}
    if cleaned in wildcard_values:
        return "ANY"

    try:
        ipaddress.ip_network(cleaned, strict=False)
        return cleaned
    except ValueError:
        try:
            ipaddress.ip_address(cleaned)
            return cleaned
        except ValueError:
            if not HOSTNAME_REGEX.match(cleaned):
                raise ValueError(
                    f"'{value}' must be an IP address, CIDR block, wildcard, or FQDN"
                )
            return cleaned.lower()


def _normalise_port_values(values: List[str]) -> List[str]:
    normalised: Set[str] = set()
    for value in values:
        for token in str(value).split(","):
            candidate = token.strip()
            if not candidate:
                continue

            if "-" in candidate:
                start_str, end_str = candidate.split("-", maxsplit=1)
                try:
                    start_port = int(start_str)
                    end_port = int(end_str)
                except ValueError as exc:
                    raise ValueError(f"Port range '{candidate}' is not valid") from exc
                if not (1 <= start_port <= 65535 and 1 <= end_port <= 65535):
                    raise ValueError(f"Port range '{candidate}' must be within 1-65535")
                if start_port > end_port:
                    raise ValueError(
                        f"Port range '{candidate}' start must be less than or equal to end"
                    )
                normalised.add(f"{start_port}-{end_port}")
            else:
                try:
                    port_num = int(candidate)
                except ValueError as exc:
                    raise ValueError(
                        f"Port '{candidate}' is not a valid number"
                    ) from exc
                if not (1 <= port_num <= 65535):
                    raise ValueError(f"Port '{candidate}' must be between 1 and 65535")
                normalised.add(str(port_num))
    if not normalised:
        raise ValueError("At least one port value is required")
    return sorted(normalised)


def _validate_url(value: Optional[str]) -> Optional[str]:
    if value is None or value.strip() == "":
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("GitHub PR URL must be a valid http(s) URL")
    return value.strip()


class EnvironmentRequest(BaseModel):
    """Schema for environment request."""

    environment_name: str = Field(..., min_length=2, max_length=50)
    region: str = Field(..., min_length=1, max_length=50)

    @field_validator("environment_name")
    @classmethod
    def validate_environment_name(cls, v: str) -> str:
        """Validate environment name format."""
        if not v or v.strip() == "":
            raise ValueError("Environment name cannot be empty")
        return v.strip()

    @field_validator("region")
    @classmethod
    def validate_region(cls, v: str) -> str:
        """Validate region."""
        if not v or v.strip() == "":
            raise ValueError("Region cannot be empty")
        return v.strip()


class OnboardingRequest(BaseModel):
    """Schema for application onboarding request."""

    app_slug: str = Field(..., min_length=4, max_length=6)
    application_name: str = Field(..., min_length=3, max_length=200)
    organization: str = Field(..., min_length=2, max_length=100)
    lob: str = Field(..., min_length=2, max_length=100)
    platform: str = Field(default="Azure", max_length=50)
    environments: List[EnvironmentRequest] = Field(..., min_length=1)
    save_as_draft: bool = Field(default=False)

    @field_validator("app_slug")
    @classmethod
    def validate_app_slug(cls, v: str) -> str:
        """Validate app slug format."""
        if not v or v.strip() == "":
            raise ValueError("App slug cannot be empty")

        v = v.strip().lower()

        if len(v) < 4:
            raise ValueError("App slug must be at least 4 characters long")

        if len(v) > 6:
            raise ValueError("App slug must be at most 6 characters long")

        if not re.match(r"^[a-z0-9]+$", v):
            raise ValueError(
                "App slug must contain only lowercase letters and numbers (no spaces or special characters)"
            )
        return v

    @field_validator("application_name")
    @classmethod
    def validate_application_name(cls, v: str) -> str:
        """Validate application name."""
        return v.strip()


class ApprovalRequest(BaseModel):
    """Schema for approval/rejection request."""

    approved: bool
    rejection_reason: Optional[str] = None

    @field_validator("rejection_reason")
    @classmethod
    def validate_rejection_reason(cls, v: Optional[str], info) -> Optional[str]:
        """Validate rejection reason is provided when rejected."""
        values = info.data
        if not values.get("approved") and not v:
            raise ValueError("Rejection reason is required when rejecting a request")
        return v.strip() if v else None


class LookupDataCreate(BaseModel):
    """Schema for creating lookup data."""

    field: str = Field(..., min_length=2, max_length=50)
    value: str = Field(..., min_length=1, max_length=100)
    abbreviation: str = Field(..., min_length=1, max_length=10)

    @field_validator("field")
    @classmethod
    def validate_field(cls, v: str) -> str:
        """Validate field type."""
        valid_fields = ["Organization", "LOB", "Environment", "Region"]
        if v not in valid_fields:
            raise ValueError(f"Field must be one of: {', '.join(valid_fields)}")
        return v

    @field_validator("abbreviation")
    @classmethod
    def validate_abbreviation(cls, v: str) -> str:
        """Validate abbreviation format."""
        if not re.match(r"^[A-Z0-9]+$", v):
            raise ValueError(
                "Abbreviation must contain only uppercase letters and numbers"
            )
        return v.strip().upper()


class FirewallRuleEntryInput(BaseModel):
    """Payload for an individual firewall rule entry."""

    source: str = Field(..., min_length=1, max_length=255)
    destination: str = Field(..., min_length=1, max_length=255)
    ports: List[str] = Field(..., min_length=1)
    protocol: str = Field(..., min_length=2, max_length=20)
    direction: str = Field(..., min_length=2, max_length=20)
    description: Optional[str] = Field(None, max_length=500)

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        return _normalise_endpoint(value)

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, value: str) -> str:
        return _normalise_endpoint(value)

    @field_validator("ports")
    @classmethod
    def validate_ports(cls, values: List[str]) -> List[str]:
        return _normalise_port_values(values)

    @field_validator("protocol")
    @classmethod
    def validate_protocol(cls, value: str) -> str:
        candidate = value.strip().upper()
        if candidate not in PROTOCOL_OPTIONS:
            raise ValueError(
                f"Protocol '{value}' is not valid. Must be one of: {', '.join(sorted(PROTOCOL_OPTIONS))}"
            )
        return candidate

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, value: str) -> str:
        candidate = value.strip().upper()
        if candidate not in DIRECTION_OPTIONS:
            raise ValueError(
                f"Direction '{value}' is not valid. Must be one of: {', '.join(sorted(DIRECTION_OPTIONS))}"
            )
        return candidate

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if value else value


class FirewallRequestCreate(BaseModel):
    """Schema for creating a firewall request with multiple rules."""

    application_name: str = Field(..., min_length=3, max_length=200)
    organization: str = Field(..., min_length=2, max_length=100)
    lob: str = Field(..., min_length=2, max_length=100)
    platform: str = Field(default="Azure", max_length=50)
    environment_scopes: List[str] = Field(..., min_length=1)
    destination_service: str = Field(..., min_length=2, max_length=200)
    justification: str = Field(..., min_length=10, max_length=4000)
    requested_effective_date: Optional[date] = None
    expires_at: Optional[date] = None
    github_pr_url: Optional[str] = Field(None, max_length=500)
    rule_entries: List[FirewallRuleEntryInput] = Field(..., min_length=1)

    @field_validator("application_name", "organization", "lob")
    @classmethod
    def validate_common_strings(cls, value: str) -> str:
        if not value or value.strip() == "":
            raise ValueError("This field cannot be empty")
        return value.strip()

    @field_validator("environment_scopes")
    @classmethod
    def validate_environment_scopes(cls, scopes: List[str]) -> List[str]:
        if not scopes:
            raise ValueError("At least one environment scope is required")
        normalised = {scope.strip().upper() for scope in scopes if scope.strip()}
        if not normalised:
            raise ValueError("Environment scope values cannot be empty")
        invalid = normalised - ENVIRONMENT_SCOPE_OPTIONS
        if invalid:
            raise ValueError(
                "Invalid environment scope(s): " + ", ".join(sorted(invalid))
            )
        return sorted(normalised)

    @field_validator("destination_service")
    @classmethod
    def validate_destination_service(cls, value: str) -> str:
        if not value or value.strip() == "":
            raise ValueError("Destination service cannot be empty")
        return value.strip()

    @field_validator("justification")
    @classmethod
    def validate_justification(cls, value: str) -> str:
        if not value or value.strip() == "":
            raise ValueError("Justification cannot be empty")
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise ValueError("Justification must be at least 10 characters long")
        return cleaned

    @field_validator("github_pr_url")
    @classmethod
    def validate_github_pr_url(cls, value: Optional[str]) -> Optional[str]:
        return _validate_url(value)

    @field_validator("expires_at")
    @classmethod
    def validate_expiry(cls, expires: Optional[date], info) -> Optional[date]:
        requested = info.data.get("requested_effective_date")
        if expires and requested and expires < requested:
            raise ValueError("Expiry date cannot be earlier than the effective date")
        return expires
