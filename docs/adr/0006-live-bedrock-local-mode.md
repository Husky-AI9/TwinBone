# ADR 0006: Opt-in live Amazon Bedrock in local mode

## Status

Accepted and live-validated on August 1, 2026 with Titan Text Embeddings v2 and Amazon Nova Lite
using fixed synthetic context.

## Context

The local product must be useful before hosting, but hackathon testing should exercise Amazon
Bedrock rather than imply that a deterministic response came from AWS. The repository must
also remain runnable in CI and by reviewers who do not have AWS credentials. Model output is
untrusted and cannot be allowed to write directly to clinical-review state.

## Decision

Local mode has two explicit runtimes:

- `BEDROCK_MODE=offline` uses deterministic 1,024-dimensional vectors and the existing bounded
  decision adapter. This is the default for tests and credential-free review.
- `BEDROCK_MODE=live` uses the Bedrock Runtime API for Titan Text Embeddings v2 and the Converse
  API for an operator-selected chat model. The runner exposes this as `-UseBedrock`.

The Converse request forces exactly one allowlisted `propose_bonetwin_decision` tool and gives
Bedrock a strict proposal schema. Bedrock may cite only retrieved memory IDs. The application
deterministically assigns evidence roles and exclusion reasons, then validates the final
`AgentDecision`, safety statement, authorized evidence set, prior-review constraint, and
human-approval constraint before persisting anything. The tool is a structured proposal
channel, not executable application code. CockroachDB retrieval remains tenant- and
subject-scoped, and application code remains the only writer.

Only fixed synthetic or explicitly de-identified content may enter either runtime. Live mode
requires IAM credentials, `bedrock:InvokeModel`, a region, and a tool-capable Converse model ID;
it does not require a separate API key. Bedrock AgentCore is not required to run Bedrock from a
local process and remains a later hosting option.

## Consequences

Developers can exercise the actual hackathon dependency without deploying the web application.
The UI identifies `LOCAL_BEDROCK` separately from `LOCAL_MOCK`. Live calls can incur AWS charges
and fail because of region, IAM, model subscription, quota, or model feature support. Offline CI
does not prove live AWS access by itself, so the separate synthetic readiness command remains the
acceptance check for each AWS account and region.
