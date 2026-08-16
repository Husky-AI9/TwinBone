"""Verify credentialed Amazon Bedrock access using synthetic-only content."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

import boto3

from services.agent.bonetwin_agent.bedrock import (
    BedrockDecisionContext,
    BedrockEvidence,
    BedrockRuntime,
)
from services.api.app.config import get_settings


def main() -> int:
    settings = get_settings()
    if settings.bedrock_mode != "live":
        raise RuntimeError("Set BEDROCK_MODE=live before checking Amazon Bedrock access")

    session = boto3.Session(
        profile_name=settings.aws_profile or None,
        region_name=settings.aws_region,
    )
    sts = cast(Any, session.client("sts"))
    sts.get_caller_identity()

    runtime = BedrockRuntime.from_aws(
        region=settings.aws_region,
        profile=settings.aws_profile,
        chat_model_id=settings.bedrock_chat_model_id,
        embedding_model_id=settings.bedrock_embedding_model_id,
        guardrail_id=settings.bedrock_guardrail_id,
        guardrail_version=settings.bedrock_guardrail_version,
        timeout_seconds=settings.bedrock_timeout_seconds,
    )
    embedding = runtime.embed("Synthetic BoneTwin readiness evidence; not a medical record.")
    context = BedrockDecisionContext(
        request_type="COMPARE_REPORTS",
        query="Organize the synthetic measurements for human review.",
        prior_review_applied=False,
        hip_series=["0.781 (2019)", "0.756 (2022)"],
        evidence=[
            BedrockEvidence(
                memory_id=UUID("51000000-0000-4000-8000-000000000001"),
                title="Synthetic verified correction",
                content="Use comparable hip sites and exclude the unsuitable lumbar value.",
                source_type="CLINICIAN_CORRECTION",
                verification_status="VERIFIED",
                disposition="USED",
                trust_score=0.93,
            )
        ],
    )
    decision = runtime.decide(context)
    print("AWS identity resolved without displaying credential or account details.")
    print(f"Titan embedding validated: {len(embedding)} dimensions.")
    print(f"Bedrock decision validated: {decision.proposed_action.action_type}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
