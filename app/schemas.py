"""Pydantic schemas for request validation."""

import re
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


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
