from unittest.mock import MagicMock

from services.api.app.config import Settings
from services.api.app.services.cockroach_store import CockroachWorkflowStore


def test_hosted_transparency_reports_only_active_runtime_services() -> None:
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.scalar_one.return_value = 23

    raw_documents = MagicMock()
    raw_documents.label = "s3-kms"
    bedrock = MagicMock()
    bedrock.embedding_model_id = "amazon.titan-embed-text-v2:0"
    bedrock.chat_model_id = "us.amazon.nova-lite-v1:0"
    mcp = MagicMock()

    store = CockroachWorkflowStore(
        engine=engine,
        settings=Settings(app_env="hosted"),
        raw_document_store=raw_documents,
        bedrock_runtime=bedrock,
        mcp_retriever=mcp,
    )

    result = store.transparency()
    services = " ".join(item["service"] for item in result.document_pipeline + result.memory_engine)
    services = f"{services} {' '.join(result.database.values())} {' '.join(result.agent.values())}"

    assert result.mode == "AWS"
    assert result.audit_event_count == 23
    assert "Amazon S3" in services
    assert "AWS KMS" in services
    assert "AWS Lambda" in services
    assert "Amazon Bedrock" in services
    assert "CockroachDB Cloud" in services
    assert "LangChain + CockroachDB Cloud managed MCP" in services
    assert "Textract" not in services
    assert "Comprehend Medical" not in services
    assert "Step Functions" not in services
