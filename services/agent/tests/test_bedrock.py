from __future__ import annotations

import json
from io import BytesIO
from typing import Any
from uuid import uuid4

import pytest

from services.agent.bonetwin_agent.bedrock import (
    DECISION_TOOL_NAME,
    BedrockDecisionContext,
    BedrockEvidence,
    BedrockInvocationError,
    BedrockRuntime,
)
from services.agent.bonetwin_agent.policies.safety import SAFETY_NOTICE


class FakeBedrockClient:
    def __init__(self, *, decision: dict[str, object] | None = None) -> None:
        self.decision = decision
        self.invoke_request: dict[str, Any] | None = None
        self.converse_request: dict[str, Any] | None = None

    def invoke_model(self, **kwargs: Any) -> dict[str, Any]:
        self.invoke_request = kwargs
        vector = [1.0] + [0.0] * 1023
        return {
            "body": BytesIO(
                json.dumps(
                    {
                        "embedding": vector,
                        "inputTextTokenCount": 5,
                        "embeddingsByType": {"float": vector},
                    }
                ).encode("utf-8")
            )
        }

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        self.converse_request = kwargs
        if self.decision is None:
            return {
                "stopReason": "end_turn",
                "output": {"message": {"content": [{"text": "free form is rejected"}]}},
            }
        return {
            "stopReason": "tool_use",
            "output": {
                "message": {
                    "content": [
                        {
                            "toolUse": {
                                "toolUseId": "tool-1",
                                "name": DECISION_TOOL_NAME,
                                "input": self.decision,
                            }
                        }
                    ]
                }
            },
        }


def _context() -> BedrockDecisionContext:
    return BedrockDecisionContext(
        request_type="COMPARE_REPORTS",
        query="Compare the synthetic reports.",
        prior_review_applied=False,
        hip_series=["0.781 (2019)", "0.756 (2022)"],
        evidence=[
            BedrockEvidence(
                memory_id=uuid4(),
                title="Verified correction",
                content="Use comparable hip sites and exclude the lumbar value.",
                source_type="CLINICIAN_CORRECTION",
                verification_status="VERIFIED",
                disposition="USED",
                trust_score=0.93,
            ),
            BedrockEvidence(
                memory_id=uuid4(),
                title="Rejected parser inference",
                content="Scanner models may be directly comparable.",
                source_type="PARSER_INFERENCE",
                verification_status="REJECTED",
                disposition="EXCLUDED",
                disposition_reason="Rejected evidence is not eligible for action context.",
                trust_score=0.11,
            ),
        ],
    )


def _decision(context: BedrockDecisionContext) -> dict[str, object]:
    return {
        "summary": "The source-backed hip measurements are organized for human review.",
        "uncertainty": "Scanner context still requires confirmation.",
        "safety_notice": SAFETY_NOTICE,
        "cited_memory_ids": [str(context.evidence[0].memory_id)],
        "proposed_action": {
            "action_type": "CREATE_CLINICIAN_REVIEW",
            "title": "Confirm scanner context",
            "rationale": "The reports contain different scanner metadata.",
            "payload": {"focus": "scanner metadata", "site": "left total hip"},
            "requires_human_approval": True,
        },
        "memory_impact_statement": "The verified correction excluded the lumbar value.",
        "counterfactual_without_key_memory": "The lumbar value would otherwise appear.",
    }


def test_titan_embedding_request_and_response_are_strict() -> None:
    client = FakeBedrockClient()
    runtime = BedrockRuntime(
        client,
        chat_model_id="test-chat-model",
        embedding_model_id="amazon.titan-embed-text-v2:0",
    )
    embedding = runtime.embed("Synthetic evidence only")
    assert len(embedding) == 1024
    assert client.invoke_request is not None
    request = json.loads(client.invoke_request["body"])
    assert request == {
        "inputText": "Synthetic evidence only",
        "dimensions": 1024,
        "normalize": True,
        "embeddingTypes": ["float"],
    }


def test_converse_forces_schema_tool_and_validates_authorized_evidence() -> None:
    context = _context()
    client = FakeBedrockClient(decision=_decision(context))
    runtime = BedrockRuntime(
        client,
        chat_model_id="test-chat-model",
        embedding_model_id="amazon.titan-embed-text-v2:0",
    )
    decision = runtime.decide(context)
    assert decision.proposed_action.action_type == "CREATE_CLINICIAN_REVIEW"
    assert decision.evidence[-1].role == "EXCLUDED"
    assert decision.evidence[-1].exclusion_reason == context.evidence[-1].disposition_reason
    assert client.converse_request is not None
    tool = client.converse_request["toolConfig"]
    assert tool["toolChoice"]["tool"]["name"] == DECISION_TOOL_NAME
    assert tool["tools"][0]["toolSpec"]["inputSchema"]["json"]["additionalProperties"] is False
    prompt = client.converse_request["messages"][0]["content"][0]["text"]
    assert "Populate every required top-level field" in prompt


def test_free_form_or_out_of_scope_bedrock_output_is_rejected() -> None:
    context = _context()
    runtime = BedrockRuntime(
        FakeBedrockClient(),
        chat_model_id="test-chat-model",
        embedding_model_id="amazon.titan-embed-text-v2:0",
    )
    with pytest.raises(BedrockInvocationError, match="forced tool"):
        runtime.decide(context)

    invalid = _decision(context)
    evidence = invalid["cited_memory_ids"]
    assert isinstance(evidence, list)
    evidence[0] = str(uuid4())
    invalid_runtime = BedrockRuntime(
        FakeBedrockClient(decision=invalid),
        chat_model_id="test-chat-model",
        embedding_model_id="amazon.titan-embed-text-v2:0",
    )
    with pytest.raises(BedrockInvocationError, match="authorized context"):
        invalid_runtime.decide(context)

    excluded = _decision(context)
    cited = excluded["cited_memory_ids"]
    assert isinstance(cited, list)
    cited[0] = str(context.evidence[-1].memory_id)
    excluded_runtime = BedrockRuntime(
        FakeBedrockClient(decision=excluded),
        chat_model_id="test-chat-model",
        embedding_model_id="amazon.titan-embed-text-v2:0",
    )
    with pytest.raises(BedrockInvocationError, match="excluded by application policy"):
        excluded_runtime.decide(context)
