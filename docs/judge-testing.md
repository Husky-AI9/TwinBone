# Local judge testing

No API key, AWS account, or cloud database is required for the local workflow. A local
CockroachDB instance is required and is started by the supplied scripts.

On Windows, verify dependencies, regenerate the demo PDFs, run tests, and build the app:

```powershell
.\scripts\verify_local_setup.ps1
```

Start CockroachDB, migrate and seed it, then start the API and web client:

```powershell
.\scripts\run_local.ps1 -SkipInstall
```

For credentialed hackathon testing with the UI and API still local, set `AWS_PROFILE`,
`AWS_REGION`, and `BEDROCK_CHAT_MODEL_ID`, then run:

```powershell
.\scripts\run_local.ps1 -UseBedrock -SkipInstall
```

The **System** screen must show `LOCAL_BEDROCK`. If it shows `LOCAL_MOCK`, no AWS model is being
called. Use only the generated synthetic PDFs in either mode.

For the fully credentialed local stack, set the Cloud SQL `DATABASE_URL`,
`COCKROACH_CLUSTER_ID`, `COCKROACH_MCP_API_KEY`, and `MCP_READONLY_DATABASE`, then run:

```powershell
.\scripts\run_local.ps1 -UseBedrock -UseCockroachCloudMcp -SkipInstall
```

The **System** screen must show `LOCAL_CLOUD_MCP`, CockroachDB Cloud as the database, and
LangChain managed-MCP retrieval. This mode applies migrations and synthetic seeds, so use only a
dedicated demo cluster.

Open `http://127.0.0.1:3000`, choose **Try demo account**, then use **Upload report** to download
the 2026 demo PDF and select
that exact file, and click **Upload and process**. The API should return `READY` with three
source-backed measurements. Continue through comparison, Memory Impact Trace, clinician
approval, and the new-session proof.

To prove persistence independently of browser state, approve the task, stop and restart the
API, then run the comparison again. The result must show `persisted_review_applied=true` and
must propose `NO_ACTION`. The transparency page must identify CockroachDB as the active local
system of record.

Use `demo-clinician` for local state-changing requests. All included reports are fictional
and visibly labeled. Do not upload a real medical document in local mode.

Cloud credentials, a public URL, and hosted judge access remain deployment-phase work.
