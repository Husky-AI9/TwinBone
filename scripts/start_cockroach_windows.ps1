param(
    [int]$SqlPort = 26257,
    [int]$HttpPort = 8080
)

$ErrorActionPreference = "Stop"
$workspaceRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$binary = Get-ChildItem -Path (Join-Path $workspaceRoot ".tools\cockroach-v26.2.4") `
    -Recurse -Filter "cockroach.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 1
if (-not $binary) {
    throw "Run scripts\install_cockroach_windows.ps1 first."
}

$existing = Get-NetTCPConnection -LocalPort $SqlPort -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    Write-Output "A process is already listening on SQL port $SqlPort."
    exit 0
}

$dataDirectory = Join-Path $workspaceRoot ".cockroach-data\phase1"
$logDirectory = Join-Path $workspaceRoot ".cockroach-data\launcher-logs"
New-Item -ItemType Directory -Path $dataDirectory, $logDirectory -Force | Out-Null
$stdout = Join-Path $logDirectory "stdout.log"
$stderr = Join-Path $logDirectory "stderr.log"

$process = Start-Process -FilePath $binary.FullName -ArgumentList @(
    "start-single-node",
    "--insecure",
    "--listen-addr=127.0.0.1:$SqlPort",
    "--http-addr=127.0.0.1:$HttpPort",
    "--store=$dataDirectory"
) -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru

for ($attempt = 0; $attempt -lt 60; $attempt++) {
    Start-Sleep -Seconds 1
    & $binary.FullName sql --insecure --host="127.0.0.1:$SqlPort" `
        --execute="SELECT 1" *> $null
    if ($LASTEXITCODE -eq 0) {
        Set-Content -LiteralPath (Join-Path $workspaceRoot ".cockroach-data\cockroach.pid") `
            -Value $process.Id
        Write-Output "CockroachDB is ready (PID $($process.Id))."
        exit 0
    }
    if ($process.HasExited) {
        break
    }
}

if (-not $process.HasExited) {
    Stop-Process -Id $process.Id
}
Get-Content -LiteralPath $stderr -Tail 80 -ErrorAction SilentlyContinue
throw "CockroachDB did not become ready within 60 seconds."
