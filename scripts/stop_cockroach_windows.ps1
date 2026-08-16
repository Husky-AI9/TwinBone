$ErrorActionPreference = "Stop"
$workspaceRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$pidFile = Join-Path $workspaceRoot ".cockroach-data\cockroach.pid"
if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Output "No BoneTwin CockroachDB PID file exists."
    exit 0
}

$cockroachProcessId = [int](Get-Content -LiteralPath $pidFile -Raw)
$process = Get-CimInstance Win32_Process -Filter "ProcessId=$cockroachProcessId" `
    -ErrorAction SilentlyContinue
$expectedStore = Join-Path $workspaceRoot ".cockroach-data\phase1"
if (-not $process -or $process.Name -ne "cockroach.exe" -or
    -not $process.CommandLine.Contains($expectedStore)) {
    throw "PID file does not identify the workspace-scoped CockroachDB process."
}

Stop-Process -Id $cockroachProcessId
Remove-Item -LiteralPath $pidFile
Write-Output "Stopped BoneTwin CockroachDB process $cockroachProcessId."
