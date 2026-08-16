param(
    [switch]$SkipInstall,
    [switch]$UseBedrock,
    [switch]$UseS3,
    [switch]$UseCockroachCloudMcp
)

$ErrorActionPreference = "Stop"
$workspaceRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
Push-Location $workspaceRoot

function Assert-LastExitCode([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE."
    }
}

try {
    if (-not $SkipInstall) {
        & python -m uv sync --locked
        Assert-LastExitCode "Python dependency installation"
        & npx pnpm install --frozen-lockfile
        Assert-LastExitCode "Node dependency installation"
    }

    if ($UseCockroachCloudMcp) {
        if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL) -or
            $env:DATABASE_URL -notmatch "cockroachlabs\.cloud") {
            throw "Set DATABASE_URL to the TLS CockroachDB Cloud SQL connection string."
        }
        if ([string]::IsNullOrWhiteSpace($env:COCKROACH_CLUSTER_ID)) {
            throw "Set COCKROACH_CLUSTER_ID from the CockroachDB Cloud cluster Overview URL."
        }
        if ([string]::IsNullOrWhiteSpace($env:COCKROACH_MCP_API_KEY)) {
            throw "Set COCKROACH_MCP_API_KEY to a dedicated CockroachDB Cloud service-account key."
        }
        if ([string]::IsNullOrWhiteSpace($env:MCP_READONLY_DATABASE)) {
            $env:MCP_READONLY_DATABASE = "bonetwin"
        }
        $env:COCKROACH_MCP_MODE = "langchain"
    }
    else {
        $cockroachBinary = Get-ChildItem -Path (Join-Path $workspaceRoot ".tools\cockroach-v26.2.4") `
            -Recurse -Filter "cockroach.exe" -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if (-not $cockroachBinary) {
            & .\scripts\install_cockroach_windows.ps1
        }
        & .\scripts\start_cockroach_windows.ps1
        $env:DATABASE_URL = "postgresql://root@127.0.0.1:26257/bonetwin?sslmode=disable"
        $env:COCKROACH_MCP_MODE = "disabled"
    }

    $env:WORKFLOW_STORE_MODE = "cockroach"
    $env:AWS_DOCUMENT_PIPELINE_MODE = "mock"
    $env:RAW_DOCUMENT_STORE_MODE = if ($UseS3) { "s3" } else { "filesystem" }
    $env:AUTH_MODE = "mock"
    $env:ALLOW_SYNTHETIC_DEMO_ONLY = "true"

    if ($UseBedrock) {
        if ([string]::IsNullOrWhiteSpace($env:BEDROCK_CHAT_MODEL_ID)) {
            $env:BEDROCK_CHAT_MODEL_ID = "amazon.nova-lite-v1:0"
            Write-Output "BEDROCK_CHAT_MODEL_ID was blank; using Amazon Nova Lite."
        }
        $env:BEDROCK_MODE = "live"
        & python -m uv run python -m scripts.check_bedrock_access
        Assert-LastExitCode "Amazon Bedrock access check"
    }
    else {
        $env:BEDROCK_MODE = "offline"
    }

    & python -m uv run python -m scripts.migrate
    Assert-LastExitCode "CockroachDB migrations"
    & python -m uv run python -m scripts.seed
    Assert-LastExitCode "Synthetic structured seed"
    if ($UseCockroachCloudMcp) {
        & python -m uv run python -m scripts.check_cockroach_cloud_mcp
        Assert-LastExitCode "LangChain CockroachDB Cloud MCP readiness"
    }
    & python -m uv run python -m scripts.generate_demo_documents
    Assert-LastExitCode "Demo PDF generation"
    if ($UseS3) {
        & python -m uv run python -m scripts.check_s3_access
        Assert-LastExitCode "Amazon S3 access check"
    }

    Write-Output "BoneTwin durable local mode is ready."
    Write-Output "Web: http://127.0.0.1:3000"
    Write-Output "API: http://127.0.0.1:8000/docs"
    if ($UseCockroachCloudMcp) {
        Write-Output "Database: CockroachDB Cloud with LangChain managed-MCP retrieval."
    }
    else {
        Write-Output "CockroachDB console: http://127.0.0.1:8080"
    }
    if ($UseBedrock) {
        Write-Output "Amazon Bedrock is active through AWS IAM credentials; no separate API key is used."
    }
    else {
        Write-Output "Amazon Bedrock is offline. No AWS credentials are required for this test mode."
    }
    if ($UseS3) {
        Write-Output "Raw synthetic uploads use presigned KMS-encrypted Amazon S3 objects."
    }
    else {
        Write-Output "Raw synthetic uploads use temporary local filesystem storage."
    }
    & npx pnpm dev
    Assert-LastExitCode "Local development servers"
}
finally {
    Pop-Location
}
