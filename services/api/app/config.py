"""Typed application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_DATABASE_URL = "postgresql://root@localhost:26257/bonetwin?sslmode=disable"


class Settings(BaseSettings):
    """BoneTwin settings with safe local defaults and redacted secrets."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "local"
    log_level: str = "INFO"
    allow_synthetic_demo_only: bool = True
    database_url: SecretStr = Field(default=SecretStr(LOCAL_DATABASE_URL), repr=False)
    db_transaction_max_retries: int = Field(default=5, ge=1, le=20)
    db_transaction_base_delay_seconds: float = Field(default=0.025, ge=0, le=10)
    db_transaction_max_delay_seconds: float = Field(default=0.5, ge=0, le=30)
    workflow_store_mode: str = "cockroach"
    cockroach_mcp_mode: str = "disabled"
    cockroach_cluster_id: str = ""
    cockroach_mcp_url: str = "https://cockroachlabs.cloud/mcp"
    cockroach_mcp_api_key: SecretStr = Field(default=SecretStr(""), repr=False)
    mcp_readonly_database: str = ""
    cockroach_mcp_timeout_seconds: int = Field(default=30, ge=5, le=120)
    auth_mode: str = "mock"
    cognito_user_pool_id: str = ""
    cognito_client_id: str = ""
    aws_region: str = "us-west-2"
    aws_profile: str = ""
    aws_document_pipeline_mode: str = "mock"
    raw_document_store_mode: str = "filesystem"
    s3_document_bucket: str = ""
    s3_document_prefix: str = "bonetwin/raw-local"
    kms_key_arn: str = ""
    raw_document_retention_days: int = Field(default=1, ge=1, le=7)
    s3_presigned_url_expiry_seconds: int = Field(default=900, ge=60, le=3600)
    bedrock_mode: str = "offline"
    bedrock_chat_model_id: str = ""
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    bedrock_guardrail_id: str = ""
    bedrock_guardrail_version: str = ""
    bedrock_timeout_seconds: int = Field(default=60, ge=10, le=300)
    cors_origins: str = "http://127.0.0.1:3000,http://localhost:3000"

    @field_validator("database_url", mode="before")
    @classmethod
    def replace_blank_database_url(cls, value: object) -> object:
        """Treat a blank local environment value as the documented safe default."""
        if value == "":
            return LOCAL_DATABASE_URL
        return value

    @field_validator("allow_synthetic_demo_only")
    @classmethod
    def require_synthetic_demo_policy(cls, value: bool) -> bool:
        """Prevent accidental startup with the public-demo data boundary disabled."""
        if not value:
            raise ValueError("ALLOW_SYNTHETIC_DEMO_ONLY must remain true")
        return value

    @field_validator("workflow_store_mode")
    @classmethod
    def validate_workflow_store_mode(cls, value: str) -> str:
        """Keep the in-memory store restricted to explicit unit-test use."""
        normalized = value.strip().lower()
        if normalized not in {"cockroach", "memory"}:
            raise ValueError("WORKFLOW_STORE_MODE must be cockroach or memory")
        return normalized

    @field_validator("bedrock_mode")
    @classmethod
    def validate_bedrock_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"offline", "live"}:
            raise ValueError("BEDROCK_MODE must be offline or live")
        return normalized

    @field_validator("raw_document_store_mode")
    @classmethod
    def validate_raw_document_store_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"filesystem", "s3"}:
            raise ValueError("RAW_DOCUMENT_STORE_MODE must be filesystem or s3")
        return normalized

    @field_validator("s3_document_prefix")
    @classmethod
    def validate_s3_document_prefix(cls, value: str) -> str:
        normalized = value.strip().strip("/")
        if not normalized or ".." in normalized.split("/"):
            raise ValueError("S3_DOCUMENT_PREFIX must be a safe non-empty key prefix")
        return normalized

    @field_validator("cockroach_mcp_mode")
    @classmethod
    def validate_cockroach_mcp_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"disabled", "langchain"}:
            raise ValueError("COCKROACH_MCP_MODE must be disabled or langchain")
        return normalized

    @model_validator(mode="after")
    def validate_live_bedrock_configuration(self) -> Settings:
        if self.bedrock_mode == "live" and not self.bedrock_chat_model_id.strip():
            raise ValueError("BEDROCK_CHAT_MODEL_ID is required when BEDROCK_MODE=live")
        if bool(self.bedrock_guardrail_id) != bool(self.bedrock_guardrail_version):
            raise ValueError(
                "BEDROCK_GUARDRAIL_ID and BEDROCK_GUARDRAIL_VERSION must be set together"
            )
        if self.raw_document_store_mode == "s3" and not self.s3_document_bucket.strip():
            raise ValueError("S3_DOCUMENT_BUCKET is required when RAW_DOCUMENT_STORE_MODE=s3")
        if self.cockroach_mcp_mode == "langchain":
            if not self.cockroach_cluster_id.strip():
                raise ValueError("COCKROACH_CLUSTER_ID is required for LangChain MCP retrieval")
            if not self.cockroach_mcp_api_key.get_secret_value().strip():
                raise ValueError("COCKROACH_MCP_API_KEY is required for LangChain MCP retrieval")
            if not self.mcp_readonly_database.strip():
                raise ValueError("MCP_READONLY_DATABASE is required for LangChain MCP retrieval")
            database_url = self.reveal_database_url()
            if "cockroachlabs.cloud" not in database_url or "sslmode=" not in database_url:
                raise ValueError(
                    "DATABASE_URL must be a TLS CockroachDB Cloud URL in LangChain MCP mode"
                )
        return self

    def reveal_database_url(self) -> str:
        """Return the URL only at the database connection boundary."""
        return self.database_url.get_secret_value()

    def reveal_cockroach_mcp_api_key(self) -> str:
        """Return the MCP bearer token only at the HTTP client boundary."""
        return self.cockroach_mcp_api_key.get_secret_value()

    @property
    def allowed_cors_origins(self) -> list[str]:
        """Return explicit local origins without wildcard credential exposure."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one immutable-by-convention settings instance per process."""
    return Settings()
