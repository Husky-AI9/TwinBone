# CockroachDB Cloud MCP setup

## Local application mode

The local UI/API can use CockroachDB Cloud as its durable store and LangChain as the managed MCP
client. Storage writes use the Cloud SQL `DATABASE_URL`; trusted-memory retrieval is gated by the
managed MCP `select_query` tool. These are deliberately separate paths.

```powershell
$env:DATABASE_URL = "postgresql://<sql-user>:<password>@<host>:26257/bonetwin?sslmode=verify-full"
$env:COCKROACH_CLUSTER_ID = "<cluster-uuid>"
$env:COCKROACH_MCP_API_KEY = "<dedicated-service-account-secret>"
$env:MCP_READONLY_DATABASE = "bonetwin"
.\scripts\run_local.ps1 -UseBedrock -UseCockroachCloudMcp -SkipInstall
```

The runner applies migrations and synthetic seed data to the configured Cloud database. Run it
only against a staging/demo cluster. To inspect connectivity separately after migration:

```powershell
$env:COCKROACH_MCP_MODE = "langchain"
python -m uv run python -m scripts.check_cockroach_cloud_mcp
```

The checker lists no credentials or record IDs. It confirms that `select_query` exists and that
the fixed synthetic memory view returns UUIDs.

## Security model

The managed endpoint is `https://cockroachlabs.cloud/mcp`. Interactive inspector tools should
use OAuth and authorize **read access only**. The non-interactive local application uses a
dedicated service-account API key, scopes every request with `mcp-cluster-id`, and loads only
`select_query`. Do not place API keys in this repository.

The database migration creates `bonetwin_mcp_reader`, a purpose-specific SQL role with
`SELECT` on exactly these fixed-demo-subject views:

- `mcp_subject_memory_trace`
- `mcp_agent_run_trace`
- `mcp_open_review_tasks`

The views omit raw content, source evidence text, embeddings, metadata, user queries, action
payloads, credentials, and direct identifiers. They are restricted to the deterministic
synthetic tenant and subject IDs.

## Cloud activation

1. Apply all migrations to the CockroachDB Cloud demo database.
2. Run `python -m uv run python -m scripts.check_mcp_readonly`.
3. Create a dedicated Cloud service account that can access only the demo cluster and generate
   its API key. CockroachDB currently requires Cluster Operator or Cluster Admin for managed MCP
   service-account access; use the lower role supported by your cluster and protect the key.
4. Keep the separate application SQL identity limited to the tables/operations required by the
   API. The MCP application code still queries only the curated views.
5. For a separate interactive inspector, configure OAuth and the single-cluster header:

   ```toml
   [mcp_servers.cockroachdb-cloud]
   url = "https://cockroachlabs.cloud/mcp"
   http_headers = { "mcp-cluster-id" = "{your-cluster-id}" }
   ```

6. During OAuth, authorize read access only.
7. Run the prompts in `docs/mcp-demo-prompts.md`.
8. Attempt a write and a query against a base table; both must be denied before judge use.

Cloud activation and live verification remain pending until you supply the SQL URL, cluster ID,
database name, and service-account API key in your local environment.
