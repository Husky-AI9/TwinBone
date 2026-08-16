param(
    [switch]$SkipInstall,
    [switch]$Start
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
    & python --version
    Assert-LastExitCode "Python discovery"
    & node --version
    Assert-LastExitCode "Node.js discovery"
    & python -m uv --version
    Assert-LastExitCode "uv discovery"
    & python -m uv run python --version
    Assert-LastExitCode "managed Python discovery"
    & npx pnpm --version
    Assert-LastExitCode "pnpm discovery"

    if (-not $SkipInstall) {
        & python -m uv sync --locked
        Assert-LastExitCode "Python dependency installation"
        & npx pnpm install --frozen-lockfile
        Assert-LastExitCode "Node dependency installation"
    }

    $cockroachBinary = Get-ChildItem -Path (Join-Path $workspaceRoot ".tools\cockroach-v26.2.4") `
        -Recurse -Filter "cockroach.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $cockroachBinary) {
        & .\scripts\install_cockroach_windows.ps1
        Assert-LastExitCode "CockroachDB installation"
    }
    & .\scripts\start_cockroach_windows.ps1
    Assert-LastExitCode "CockroachDB startup"
    $env:DATABASE_URL = "postgresql://root@127.0.0.1:26257/bonetwin?sslmode=disable"
    $env:WORKFLOW_STORE_MODE = "cockroach"
    $env:AWS_DOCUMENT_PIPELINE_MODE = "mock"
    $env:AUTH_MODE = "mock"
    $env:ALLOW_SYNTHETIC_DEMO_ONLY = "true"
    $env:BEDROCK_MODE = "offline"
    & python -m uv run python -m scripts.migrate
    Assert-LastExitCode "CockroachDB migrations"
    & python -m uv run python -m scripts.seed
    Assert-LastExitCode "Structured synthetic seed"

    & python -m uv run python -m scripts.generate_demo_documents
    Assert-LastExitCode "Demo PDF generation"
    & python -m uv run pytest -m "not integration"
    Assert-LastExitCode "Python local tests"
    $env:BONETWIN_RUN_DB_TESTS = "1"
    & python -m uv run pytest -m integration
    Assert-LastExitCode "CockroachDB integration tests"
    & python -m uv run ruff format --check .
    Assert-LastExitCode "Python formatting"
    & python -m uv run ruff check .
    Assert-LastExitCode "Python lint"
    & python -m uv run mypy services evaluations scripts
    Assert-LastExitCode "Python type check"
    & python -m uv run python -m scripts.check_mcp_readonly
    Assert-LastExitCode "Read-only MCP boundary"
    & python -m uv run python -m scripts.run_cockroach_privilege_skill
    Assert-LastExitCode "CockroachDB Agent Skill evidence"
    & python -m uv run python -m evaluations.runners.memory_quality --check
    Assert-LastExitCode "Memory quality evaluation"
    & python -m uv run python scripts\check_no_secrets.py
    Assert-LastExitCode "Secret signature scan"
    & npx pnpm format:check
    Assert-LastExitCode "Node formatting"
    & npx pnpm lint
    Assert-LastExitCode "Node lint"
    & npx pnpm typecheck
    Assert-LastExitCode "TypeScript type check"
    & npx pnpm test
    Assert-LastExitCode "Web tests"
    & npx pnpm build
    Assert-LastExitCode "Production build"
    & npx pnpm --filter @bonetwin/infrastructure synth --quiet
    Assert-LastExitCode "AWS CDK synthesis"

    Write-Output "BoneTwin durable offline verification passed. No API key is required."
    Write-Output "CockroachDB is the active local system of record."
    Write-Output "Demo PDFs: $workspaceRoot\output\pdf"
    Write-Output "Start command: .\scripts\run_local.ps1 -SkipInstall"

    if ($Start) {
        & npx pnpm dev
        Assert-LastExitCode "Local development servers"
    }
}
finally {
    Pop-Location
}
