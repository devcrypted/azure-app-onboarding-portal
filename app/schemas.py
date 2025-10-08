"""Pydantic schemas for request validation."""

import ipaddress
import re
from datetime import date
from typing import Dict, List, Optional, Set
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

HOSTNAME_REGEX = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.?$"
)
PROTOCOL_OPTIONS = {"TCP", "UDP", "ICMP", "ESP", "AH", "GRE", "ANY"}
DIRECTION_OPTIONS = {"INBOUND", "OUTBOUND", "BIDIRECTIONAL"}
AZURE_NAME_REGEX = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
APPLICATION_RULE_PROTOCOLS = {"HTTP", "HTTPS", "MSSQL"}
NETWORK_RULE_PROTOCOLS = {"ANY", "TCP", "UDP", "ICMP"}
NAT_RULE_PROTOCOLS = {"ANY", "TCP", "UDP"}
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


def _validate_collection_name(value: str, *, field_name: str) -> str:
    if not value or value.strip() == "":
        raise ValueError(f"{field_name} cannot be empty")
    cleaned = value.strip()
    if not AZURE_NAME_REGEX.fullmatch(cleaned):
        raise ValueError(
            f"{field_name} must be 1-80 characters and contain only letters, numbers, underscores, or hyphens"
        )
    return cleaned


def _normalise_address_list(
    values: List[str], *, allow_empty: bool = False
) -> List[str]:
    normalised = []
    for value in values:
        if value is None:
            continue
        normalised.append(_normalise_endpoint(value))
    if not normalised and not allow_empty:
        raise ValueError("At least one address value is required")
    # Preserve order but remove duplicates
    return list(dict.fromkeys(normalised))


def _normalise_string_list(values: List[str]) -> List[str]:
    cleaned: List[str] = []
    for value in values:
        if value is None:
            continue
        candidate = value.strip()
        if candidate:
            cleaned.append(candidate)
    return list(dict.fromkeys(cleaned))


def _validate_priority(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    if not (100 <= value <= 65000):
        raise ValueError("Priority must be between 100 and 65000")
    if value % 100 != 0:
        raise ValueError("Priority must be in increments of 100")
    return value


class FirewallRuleBase(BaseModel):
    """Common attributes shared by all firewall rule types."""

    name: str = Field(..., max_length=80)
    ritm_number: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = Field(None, max_length=500)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _validate_collection_name(value, field_name="Rule name")

    @field_validator("ritm_number")
    @classmethod
    def validate_ritm(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if value else None

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if value else None


class ApplicationRuleProtocol(BaseModel):
    """Protocol definition for an application rule."""

    port: int = Field(..., ge=1, le=65535)
    type: str

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        candidate = value.strip().upper()
        if candidate not in APPLICATION_RULE_PROTOCOLS:
            raise ValueError(
                "Application rule protocol must be one of: "
                + ", ".join(sorted(APPLICATION_RULE_PROTOCOLS))
            )
        # Azure expects specific casing, e.g. Https
        return candidate.capitalize()


class ApplicationRuleInput(FirewallRuleBase):
    collection_type: Literal["APPLICATION"] = "APPLICATION"
    protocols: List[ApplicationRuleProtocol] = Field(..., min_length=1)
    source_ip_addresses: List[str] = Field(..., min_length=1)
    source_ip_groups: List[str] = Field(default_factory=list)
    destination_fqdns: List[str] = Field(default_factory=list)
    destination_addresses: List[str] = Field(default_factory=list)

    @field_validator("source_ip_addresses")
    @classmethod
    def validate_sources(cls, values: List[str]) -> List[str]:
        return _normalise_address_list(values)

    @field_validator("source_ip_groups")
    @classmethod
    def validate_group_names(cls, values: List[str]) -> List[str]:
        names = [_validate_collection_name(v, field_name="IP group") for v in values]
        return list(dict.fromkeys(names))

    @field_validator("destination_addresses")
    @classmethod
    def validate_app_dest_addresses(cls, values: List[str]) -> List[str]:
        return _normalise_address_list(values, allow_empty=True)

    @field_validator("destination_fqdns")
    @classmethod
    def validate_dest_fqdns(cls, values: List[str]) -> List[str]:
        return _normalise_address_list(values, allow_empty=True)


class NetworkRuleInput(FirewallRuleBase):
    collection_type: Literal["NETWORK"] = "NETWORK"
    protocols: List[str] = Field(..., min_length=1)
    source_ip_addresses: List[str] = Field(..., min_length=1)
    source_ip_groups: List[str] = Field(default_factory=list)
    destination_ip_addresses: List[str] = Field(..., min_length=1)
    destination_ip_groups: List[str] = Field(default_factory=list)
    destination_ports: List[str] = Field(..., min_length=1)
    destination_fqdns: List[str] = Field(default_factory=list)

    @field_validator("protocols")
    @classmethod
    def validate_protocols(cls, values: List[str]) -> List[str]:
        cleaned = []
        for value in values:
            candidate = value.strip().upper()
            if candidate not in NETWORK_RULE_PROTOCOLS:
                raise ValueError(
                    "Network rule protocol must be one of: "
                    + ", ".join(sorted(NETWORK_RULE_PROTOCOLS))
                )
            cleaned.append(candidate)
        return list(dict.fromkeys(cleaned))

    @field_validator("source_ip_addresses", "destination_ip_addresses")
    @classmethod
    def validate_ip_lists(cls, values: List[str]) -> List[str]:
        return _normalise_address_list(values)

    @field_validator("source_ip_groups", "destination_ip_groups")
    @classmethod
    def validate_group_lists(cls, values: List[str]) -> List[str]:
        names = [_validate_collection_name(v, field_name="IP group") for v in values]
        return list(dict.fromkeys(names))

    @field_validator("destination_ports")
    @classmethod
    def validate_ports(cls, values: List[str]) -> List[str]:
        return _normalise_port_values(values)

    @field_validator("destination_fqdns")
    @classmethod
    def validate_network_dest_fqdns(cls, values: List[str]) -> List[str]:
        return _normalise_address_list(values, allow_empty=True)


class NatRuleInput(FirewallRuleBase):
    collection_type: Literal["NAT"] = "NAT"
    protocols: List[str] = Field(..., min_length=1)
    source_ip_addresses: List[str] = Field(..., min_length=1)
    source_ip_groups: List[str] = Field(default_factory=list)
    destination_address: str
    destination_ports: List[str] = Field(..., min_length=1)
    translated_address: str
    translated_port: int = Field(..., ge=1, le=65535)

    @field_validator("protocols")
    @classmethod
    def validate_nat_protocols(cls, values: List[str]) -> List[str]:
        cleaned = []
        for value in values:
            candidate = value.strip().upper()
            if candidate not in NAT_RULE_PROTOCOLS:
                raise ValueError(
                    "NAT rule protocol must be one of: "
                    + ", ".join(sorted(NAT_RULE_PROTOCOLS))
                )
            cleaned.append(candidate)
        return list(dict.fromkeys(cleaned))

    @field_validator("source_ip_addresses")
    @classmethod
    def validate_nat_sources(cls, values: List[str]) -> List[str]:
        return _normalise_address_list(values)

    @field_validator("source_ip_groups")
    @classmethod
    def validate_nat_groups(cls, values: List[str]) -> List[str]:
        names = [_validate_collection_name(v, field_name="IP group") for v in values]
        return list(dict.fromkeys(names))

    @field_validator("destination_address", "translated_address")
    @classmethod
    def validate_nat_addresses(cls, value: str) -> str:
        return _normalise_endpoint(value)

    @field_validator("destination_ports")
    @classmethod
    def validate_nat_ports(cls, values: List[str]) -> List[str]:
        return _normalise_port_values(values)


class ApplicationRuleGroupInput(BaseModel):
    action: str
    priority: Optional[int] = None
    rules: List[ApplicationRuleInput] = Field(..., min_length=1)

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        candidate = value.strip().upper()
        if candidate not in {"ALLOW", "DENY"}:
            raise ValueError("Application rule action must be Allow or Deny")
        return candidate.capitalize()

    @field_validator("priority")
    @classmethod
    def validate_priority_value(cls, value: Optional[int]) -> Optional[int]:
        return _validate_priority(value)


class NetworkRuleGroupInput(BaseModel):
    action: str
    priority: Optional[int] = None
    rules: List[NetworkRuleInput] = Field(..., min_length=1)

    @field_validator("action")
    @classmethod
    def validate_network_action(cls, value: str) -> str:
        candidate = value.strip().upper()
        if candidate not in {"ALLOW", "DENY"}:
            raise ValueError("Network rule action must be Allow or Deny")
        return candidate.capitalize()

    @field_validator("priority")
    @classmethod
    def validate_network_priority(cls, value: Optional[int]) -> Optional[int]:
        return _validate_priority(value)


class NatRuleGroupInput(BaseModel):
    action: str
    priority: Optional[int] = None
    rules: List[NatRuleInput] = Field(..., min_length=1)

    @field_validator("action")
    @classmethod
    def validate_nat_action(cls, value: str) -> str:
        candidate = value.strip().upper()
        if candidate != "DNAT":
            raise ValueError("NAT rule action must be Dnat")
        return "Dnat"

    @field_validator("priority")
    @classmethod
    def validate_nat_priority(cls, value: Optional[int]) -> Optional[int]:
        return _validate_priority(value)


class FirewallRequestCreate(BaseModel):
    """Schema for creating a firewall request with structured rule collections."""

    source_application_id: int = Field(..., gt=0)
    collection_name: str = Field(..., min_length=1, max_length=80)
    ip_groups: Dict[str, List[str]] = Field(default_factory=dict)
    environment_scopes: List[str] = Field(..., min_length=1)
    destination_service: str = Field(..., min_length=2, max_length=200)
    justification: str = Field(..., min_length=10, max_length=4000)
    requested_effective_date: Optional[date] = None
    expires_at: Optional[date] = None
    github_pr_url: Optional[str] = Field(None, max_length=500)
    application_rules: Optional[ApplicationRuleGroupInput] = None
    network_rules: Optional[NetworkRuleGroupInput] = None
    nat_rules: Optional[NatRuleGroupInput] = None

    @field_validator("collection_name")
    @classmethod
    def validate_collection_name(cls, value: str) -> str:
        return _validate_collection_name(value, field_name="Collection name")

    @field_validator("ip_groups")
    @classmethod
    def validate_ip_groups(cls, value: Dict[str, List[str]]) -> Dict[str, List[str]]:
        cleaned: Dict[str, List[str]] = {}
        for group_name, members in value.items():
            cleaned_name = _validate_collection_name(
                group_name, field_name="IP group name"
            )
            cleaned[cleaned_name] = _normalise_string_list(members)
        return cleaned

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

    @model_validator(mode="after")
    def ensure_rule_group_present(self):
        if not any([self.application_rules, self.network_rules, self.nat_rules]):
            raise ValueError(
                "At least one rule group (application, network, or NAT) is required"
            )
        return self
