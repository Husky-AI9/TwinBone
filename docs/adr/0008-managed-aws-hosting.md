# ADR 0008: Repository-connected managed AWS hosting

- Status: accepted
- Date: 2026-08-16

## Context

The hackathon requires a functional application deployed on AWS. BoneTwin is a pnpm Next.js
monorepo plus a Python API, and the deployment should be reproducible by connecting GitHub and
setting environment variables rather than maintaining Kubernetes, an image registry, or custom
deployment scripts. AWS App Runner's source-code Python runtime currently supports Python 3.11,
while the local project originally required 3.12.

## Decision

Use AWS Amplify Hosting for the web application and AWS App Runner for the API. Both services
track the public GitHub `main` branch. Keep the API compatible with Python 3.11 through 3.13 by
using `TypeVar`/`Generic` syntax instead of Python 3.12-only parameter syntax. Keep local
development on Python 3.12 and retain the same lockfile, strict schemas, tests, and behavior.

App Runner runs migrations and the idempotent synthetic seed before importing the API. The demo
uses one App Runner instance to avoid concurrent migration startup. Secret runtime values are
referenced from AWS Secrets Manager. Amplify receives only the public App Runner URL.

Amazon Bedrock is the required live AWS AI service. AgentCore and the CDK contract stacks are not
part of this minimal deployment and are not represented as deployed.

## Consequences

- A push to `main` automatically redeploys both services.
- No local Docker daemon, AWS CLI, ECR repository, or hand-built server is required.
- CockroachDB Cloud remains the only durable application state store.
- The public demo remains synthetic-only and uses the existing bounded demo identity. Cognito is
  still required before treating the system as a general public or real-data service.
- Scale-out must stay at one instance until migrations move to a separate release task.
