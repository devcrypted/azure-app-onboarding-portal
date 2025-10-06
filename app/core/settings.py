"""Application settings powered by Pydantic."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import quote_plus, urlencode

from pydantic import BaseModel, Field, PrivateAttr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root directory (one level up from app/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class OAuthSettings(BaseModel):
    """Settings for OAuth/OpenID Connect providers."""

    authority: Optional[str] = Field(default=None, alias="OAUTH_AUTHORITY")
    client_id: Optional[str] = Field(default=None, alias="OAUTH_CLIENT_ID")
    client_secret: Optional[str] = Field(default=None, alias="OAUTH_CLIENT_SECRET")
    redirect_uri: Optional[str] = Field(default=None, alias="OAUTH_REDIRECT_URI")
    scopes: list[str] = Field(default_factory=list, alias="OAUTH_SCOPES")

    @field_validator("scopes", mode="before")
    @classmethod
    def parse_scopes(cls, value: object) -> list[str]:
        """Accept comma or space separated scope strings."""
        if value is None:
            return []
        if isinstance(value, list):
            return [scope.strip() for scope in value if scope and scope.strip()]
        if isinstance(value, str):
            separators = [",", " "]
            scopes: list[str] = [value]
            for sep in separators:
                if sep in value:
                    scopes = [item.strip() for item in value.split(sep)]
                    break
            return [scope for scope in scopes if scope]
        raise TypeError("Invalid scope configuration")


class EmailSettings(BaseModel):
    """Outbound email/notification settings."""

    smtp_server: Optional[str] = Field(default=None, alias="EMAIL_SMTP_SERVER")
    smtp_port: int = Field(default=587, alias="EMAIL_SMTP_PORT")
    username: Optional[str] = Field(default=None, alias="EMAIL_USERNAME")
    password: Optional[str] = Field(default=None, alias="EMAIL_PASSWORD")
    use_tls: bool = Field(default=True, alias="EMAIL_USE_TLS")

    @field_validator("smtp_port", mode="before")
    @classmethod
    def cast_port(cls, value: object) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        raise ValueError("SMTP port must be an integer")

    @field_validator("use_tls", mode="before")
    @classmethod
    def cast_tls_flag(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in {"1", "true", "yes", "on"}
        return bool(value)


class AzureCommunicationsSettings(BaseModel):
    """Azure Communication Services configuration."""

    connection_string: Optional[str] = Field(
        default=None, alias="ACS_CONNECTION_STRING"
    )
    sender: Optional[str] = Field(default=None, alias="ACS_SENDER")


class AppSettings(BaseSettings):
    """Top-level application settings object."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    secret_key: str = Field(
        default="dev-secret-key-change-in-production", alias="SECRET_KEY"
    )
    admin_emails_raw: Optional[str] = Field(default=None, alias="ADMIN_EMAILS")
    _admin_emails: list[str] = PrivateAttr(default_factory=lambda: ["admin@tradex.com"])

    db_type: Literal["sqlite", "mssql"] = Field(default="sqlite", alias="DB_TYPE")
    sqlalchemy_database_uri_override: Optional[str] = Field(
        default=None, alias="SQLALCHEMY_DATABASE_URI"
    )
    sqlite_db_path: str = Field(default="instance/tradex.db", alias="SQLITE_DB_PATH")
    mssql_server: Optional[str] = Field(default=None, alias="MSSQL_SERVER")
    mssql_database: Optional[str] = Field(default=None, alias="MSSQL_DATABASE")
    mssql_username: Optional[str] = Field(default=None, alias="MSSQL_USERNAME")
    mssql_password: Optional[str] = Field(default=None, alias="MSSQL_PASSWORD")
    mssql_driver: str = Field(
        default="ODBC Driver 18 for SQL Server", alias="MSSQL_DRIVER"
    )
    azure_sql_connection_string: Optional[str] = Field(
        default=None, alias="AZURE_SQL_CONNECTIONSTRING"
    )
    mssql_connection_string: Optional[str] = Field(
        default=None, alias="MSSQL_CONNECTION_STRING"
    )
    sqlalchemy_echo: bool = Field(default=False, alias="SQLALCHEMY_ECHO")

    session_type: str = Field(default="filesystem", alias="SESSION_TYPE")
    permanent_session_lifetime: int = Field(
        default=3600, alias="PERMANENT_SESSION_LIFETIME"
    )

    # Workflow configuration
    expedite_threshold_days: int = Field(default=2, alias="EXPEDITE_THRESHOLD_DAYS")
    auto_escalate_days: int = Field(default=5, alias="AUTO_ESCALATE_DAYS")
    business_days_only: bool = Field(default=True, alias="BUSINESS_DAYS_ONLY")

    oauth: OAuthSettings = Field(default_factory=OAuthSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    acs: AzureCommunicationsSettings = Field(
        default_factory=AzureCommunicationsSettings
    )

    @model_validator(mode="after")
    def populate_admin_emails(self) -> "AppSettings":
        raw = self.admin_emails_raw
        default_emails = ["admin@tradex.com"]
        if raw is None:
            self._admin_emails = default_emails
            return self

        parsed = self._parse_admin_emails(raw)
        self._admin_emails = parsed or default_emails
        return self

    @field_validator("sqlalchemy_echo", mode="before")
    @classmethod
    def cast_sqlalchemy_echo(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @field_validator("permanent_session_lifetime", mode="before")
    @classmethod
    def cast_session_lifetime(cls, value: object) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        raise ValueError("PERMANENT_SESSION_LIFETIME must be numeric")

    @staticmethod
    def _parse_admin_emails(raw: str) -> list[str]:
        candidate = raw.strip()
        if not candidate:
            return []
        if candidate.startswith("["):
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError:
                data = None
            if isinstance(data, list):
                return [str(item).strip() for item in data if str(item).strip()]
        return [email.strip() for email in candidate.split(",") if email.strip()]

    @property
    def admin_emails(self) -> list[str]:
        return list(self._admin_emails)

    @property
    def sqlalchemy_database_uri(self) -> str:
        """Construct SQLAlchemy database URI based on configuration."""
        if self.sqlalchemy_database_uri_override:
            return self.sqlalchemy_database_uri_override

        raw_connection_string = (
            self.azure_sql_connection_string or self.mssql_connection_string
        )
        if raw_connection_string:
            return self._build_uri_from_connection_string(raw_connection_string)

        if self.db_type == "mssql":
            required = [
                ("MSSQL_SERVER", self.mssql_server),
                ("MSSQL_DATABASE", self.mssql_database),
                ("MSSQL_USERNAME", self.mssql_username),
                ("MSSQL_PASSWORD", self.mssql_password),
            ]
            missing = [config_name for config_name, value in required if not value]
            if missing:
                joined = ", ".join(missing)
                raise ValueError(
                    "Missing required MSSQL configuration values: "
                    f"{joined}. Configure the variables in your environment or .env file."
                )
            driver = quote_plus(self.mssql_driver)
            password = quote_plus(self.mssql_password or "")
            username = quote_plus(self.mssql_username or "")
            return (
                f"mssql+pyodbc://{username}:{password}@{self.mssql_server}/{self.mssql_database}"
                f"?driver={driver}&TrustServerCertificate=yes"
            )

        sqlite_path = Path(self.sqlite_db_path)
        if not sqlite_path.is_absolute():
            sqlite_path = (BASE_DIR / sqlite_path).resolve()
        return f"sqlite:///{sqlite_path.as_posix()}"

    @staticmethod
    def _parse_connection_pairs(raw: str) -> dict[str, str]:
        pairs: dict[str, str] = {}
        for fragment in raw.split(";"):
            cleaned = fragment.strip()
            if not cleaned or "=" not in cleaned:
                continue
            key, value = cleaned.split("=", 1)
            pairs[key.strip().lower()] = value.strip()
        return pairs

    @staticmethod
    def _normalize_server(server: str) -> tuple[str, Optional[str]]:
        cleaned = server.strip()
        if cleaned.lower().startswith("tcp:"):
            cleaned = cleaned[4:]
        port: Optional[str] = None
        if "," in cleaned:
            cleaned, port_part = cleaned.split(",", 1)
            port = port_part.strip()
        return cleaned, port if port else None

    def _build_uri_from_connection_string(self, raw: str) -> str:
        data = self._parse_connection_pairs(raw)

        server = data.get("server") or data.get("data source")
        database = data.get("database") or data.get("initial catalog")
        username = (
            data.get("user id")
            or data.get("uid")
            or data.get("username")
            or data.get("user")
        )
        password = data.get("password") or data.get("pwd") or ""
        driver = data.get("driver") or self.mssql_driver

        if not server or not database or not username:
            missing = [
                name
                for name, value in (
                    ("Server", server),
                    ("Database", database),
                    ("User", username),
                )
                if not value
            ]
            joined = ", ".join(missing)
            raise ValueError(
                "Invalid MSSQL connection string provided. Missing values: "
                f"{joined}."
            )

        host, port = self._normalize_server(server)
        encoded_username = quote_plus(username)
        encoded_password = quote_plus(password)

        query_params: dict[str, str] = {
            "driver": self._ensure_driver_keyword(driver),
        }

        for key in ("encrypt", "trustservercertificate", "trust server certificate"):
            value = data.get(key)
            if value is not None:
                canonical_key = (
                    "Encrypt" if "encrypt" in key else "TrustServerCertificate"
                )
                query_params[canonical_key] = value

        timeout = data.get("connection timeout") or data.get("timeout")
        if timeout:
            query_params["Connection Timeout"] = timeout

        query_string = urlencode(query_params, quote_via=quote_plus)

        location = host
        if port:
            location = f"{host}:{port}"

        return (
            f"mssql+pyodbc://{encoded_username}:{encoded_password}@{location}/{database}"
            f"?{query_string}"
        )

    @staticmethod
    def _ensure_driver_keyword(driver: str) -> str:
        cleaned = driver.strip()
        if cleaned.startswith("{") and cleaned.endswith("}"):
            cleaned = cleaned[1:-1]
        return cleaned

    @property
    def workflow_config(self) -> dict[str, object]:
        """Get workflow configuration."""
        return {
            "EXPEDITE_THRESHOLD_DAYS": self.expedite_threshold_days,
            "AUTO_ESCALATE_DAYS": self.auto_escalate_days,
            "EDITABLE_STATUSES": ["DRAFT"],
            "CANCELLABLE_STATUSES": ["DRAFT", "PENDING"],
            "EXPEDITABLE_STATUSES": ["PENDING"],
            "BUSINESS_DAYS_ONLY": self.business_days_only,
            "COMMENTABLE_STATUSES": [
                "DRAFT",
                "PENDING",
                "APPROVED",
                "SUBSCRIPTION_ASSIGNED",
                "FOUNDATION_INFRA",
                "INFRASTRUCTURE",
                "HANDOVER",
            ],
            "STATUS_DISPLAY_NAMES": {
                "DRAFT": "Draft",
                "PENDING": "Pending Approval",
                "APPROVED": "Approved",
                "REJECTED": "Rejected",
                "CANCELLED": "Cancelled",
                "COMPLETED": "Completed",
            },
            "STAGE_DISPLAY_NAMES": {
                "REQUEST_RAISED": "Request Raised",
                "PENDING_APPROVAL": "Pending Approval",
                "APPROVED": "Approved",
                "SUBSCRIPTION_ASSIGNMENT": "Subscription Assignment",
                "FOUNDATION_INFRA": "Foundation Infrastructure",
                "INFRASTRUCTURE": "Infrastructure Setup",
                "HANDOVER": "Handover",
                "REJECTED": "Rejected",
                "CANCELLED": "Cancelled",
            },
        }

    def as_flask_config(self) -> dict[str, object]:
        """Render settings as a mapping compatible with Flask.config."""
        return {
            "SECRET_KEY": self.secret_key,
            "SQLALCHEMY_DATABASE_URI": self.sqlalchemy_database_uri,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SQLALCHEMY_ECHO": self.sqlalchemy_echo,
            "SESSION_TYPE": self.session_type,
            "PERMANENT_SESSION_LIFETIME": self.permanent_session_lifetime,
            "ADMIN_EMAILS": self.admin_emails,
            "WORKFLOW_CONFIG": self.workflow_config,
        }
