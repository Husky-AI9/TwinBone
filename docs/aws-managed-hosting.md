# AWS managed hosting

BoneTwin uses two repository-connected AWS services so a push to `main` can deploy the complete
synthetic demo without a local AWS CLI:

- AWS App Runner builds and serves the FastAPI API from the repository root using
  `apprunner.yaml`.
- AWS Amplify Hosting builds and serves the Next.js application using `amplify.yml`.
- CockroachDB Cloud remains the durable system of record and managed-MCP retrieval boundary.
- Amazon Bedrock provides Titan embeddings and the schema-validated agent decision.

This is the smallest hosted configuration that meets the hackathon requirement for an agentic
application with CockroachDB memory deployed on AWS. AgentCore, Cognito, Textract, and the CDK
contract stacks are not required for this demo deployment and must not be claimed as live unless
they are separately deployed and verified.

## Before connecting the repository

1. Push the repository to a public GitHub `main` branch.
2. Use a dedicated CockroachDB Cloud demo cluster containing no real patient data.
3. Confirm the Bedrock chat model is enabled in the same AWS region as App Runner.
4. Create three AWS Secrets Manager secrets in that region:
   - `bonetwin/database-url`: the complete TLS CockroachDB SQL URL.
   - `bonetwin/cockroach-mcp-api-key`: the dedicated Cloud service-account key.
   - `bonetwin/bedrock-api-key`: the Bedrock API key.

The secret values never belong in GitHub, `amplify.yml`, or `apprunner.yaml`.

## 1. Create the App Runner API

In the AWS console, open **App Runner**, choose **Create service**, and use:

| Console field        | Value                                     |
| -------------------- | ----------------------------------------- |
| Source               | Source code repository                    |
| Provider             | GitHub                                    |
| Repository           | The public BoneTwin repository            |
| Branch               | `main`                                    |
| Source directory     | `/`                                       |
| Deployment trigger   | Automatic                                 |
| Configuration source | Use a configuration file                  |
| Configuration file   | `apprunner.yaml`                          |
| Service name         | `bonetwin-api`                            |
| Port                 | `8000` (read from the configuration file) |
| Health-check path    | `/health/ready`                           |
| Minimum instances    | `1`                                       |
| Maximum instances    | `1` for the synthetic hackathon demo      |

Add these plain-text runtime variables in App Runner:

```text
AWS_REGION=<the App Runner region>
BEDROCK_MODE=live
BEDROCK_CHAT_MODEL_ID=<enabled Converse/tool-use model ID>
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
COCKROACH_MCP_MODE=langchain
COCKROACH_CLUSTER_ID=<CockroachDB Cloud cluster UUID>
MCP_READONLY_DATABASE=<database name, normally bonetwin>
CORS_ORIGINS=http://localhost:3000
```

Add these as **secret environment variables**, referencing the three Secrets Manager ARNs:

```text
DATABASE_URL                -> bonetwin/database-url
COCKROACH_MCP_API_KEY       -> bonetwin/cockroach-mcp-api-key
AWS_BEARER_TOKEN_BEDROCK    -> bonetwin/bedrock-api-key
```

The App Runner instance role must be allowed to read those three secret ARNs. A Bedrock API key
is restricted to Bedrock runtime operations, so no AWS access key is stored in the application.
If an IAM instance role is used for Bedrock instead, omit `AWS_BEARER_TOKEN_BEDROCK` and grant
only `bedrock:InvokeModel` for the two configured models.

Create the service and wait for `/health/ready` to return `status: ready`. Startup applies the
reviewed migrations and idempotent synthetic seed. Keep maximum instances at one for the demo so
two new instances cannot attempt the initial migration simultaneously.

## 2. Create the Amplify web application

Open **AWS Amplify**, choose **Deploy an app**, connect the same GitHub repository, choose `main`,
and set the monorepo application root to:

```text
apps/web
```

Amplify should detect the root `amplify.yml`. Confirm that
`AMPLIFY_MONOREPO_APP_ROOT=apps/web`, then add these two non-secret environment variables using
the App Runner service URL without a trailing slash:

```text
BONETWIN_API_URL=https://<app-runner-service>.<region>.awsapprunner.com
NEXT_PUBLIC_BONETWIN_API_URL=https://<app-runner-service>.<region>.awsapprunner.com
```

Choose **Save and deploy**. Amplify produces the public `amplifyapp.com` URL and automatically
redeploys future `main` pushes.

## 3. Finish CORS and verify

Return to App Runner and replace the temporary CORS value with the exact Amplify origin:

```text
CORS_ORIGINS=https://main.<amplify-app-id>.amplifyapp.com
```

Deploy the App Runner configuration change, then verify:

1. Open the Amplify URL and choose **Try demo account**.
2. Upload only one of the included synthetic PDFs.
3. Confirm the parsed report reaches `READY`.
4. Run the comparison and open **System**.
5. Confirm `LOCAL_CLOUD_MCP`, CockroachDB Cloud, LangChain MCP retrieval, and the configured
   Bedrock models are visible.
6. Approve the review, open a new UI session, and confirm the prior decision changes the next
   run.
7. Stop and start App Runner once and confirm the durable decision still exists.

## Hackathon evidence to capture

- Public Amplify URL and public GitHub URL.
- App Runner service screen showing the AWS-hosted API without exposing environment values.
- System screen showing live Bedrock, CockroachDB Cloud, and Managed MCP.
- CockroachDB vector index and the read-only MCP trace.
- A public YouTube or Vimeo video shorter than three minutes.

Do not claim AgentCore, Cognito, Textract, Comprehend Medical, Step Functions, S3, or the CDK
contract stacks as deployed unless their real application paths are separately completed and
tested.
