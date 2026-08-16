from pydantic import ValidationError
from pytest import raises

from services.api.app.config import LOCAL_DATABASE_URL, Settings


def test_blank_database_url_uses_safe_local_default() -> None:
    settings = Settings.model_validate({"database_url": ""})
    assert settings.reveal_database_url() == LOCAL_DATABASE_URL
    assert LOCAL_DATABASE_URL not in repr(settings)


def test_synthetic_demo_policy_cannot_be_disabled() -> None:
    with raises(ValidationError, match="ALLOW_SYNTHETIC_DEMO_ONLY"):
        Settings.model_validate({"allow_synthetic_demo_only": False})


def test_live_bedrock_requires_chat_model_and_guardrail_pair() -> None:
    with raises(ValidationError, match="BEDROCK_CHAT_MODEL_ID"):
        Settings.model_validate({"bedrock_mode": "live", "bedrock_chat_model_id": ""})
    with raises(ValidationError, match="must be set together"):
        Settings.model_validate({"bedrock_guardrail_id": "guardrail-only"})
    settings = Settings.model_validate(
        {
            "bedrock_mode": "live",
            "bedrock_chat_model_id": "converse-tool-model",
            "bedrock_guardrail_id": "guardrail-id",
            "bedrock_guardrail_version": "1",
        }
    )
    assert settings.bedrock_mode == "live"


def test_s3_raw_storage_requires_bucket_and_safe_prefix() -> None:
    with raises(ValidationError, match="S3_DOCUMENT_BUCKET"):
        Settings.model_validate({"raw_document_store_mode": "s3", "s3_document_bucket": ""})
    with raises(ValidationError, match="safe non-empty key prefix"):
        Settings.model_validate({"s3_document_prefix": "../unsafe"})
    settings = Settings.model_validate(
        {
            "raw_document_store_mode": "s3",
            "s3_document_bucket": "synthetic-bucket",
        }
    )
    assert settings.raw_document_store_mode == "s3"
