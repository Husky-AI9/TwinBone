param(
    [string]$Destination = (Join-Path $PSScriptRoot "..\.tools\cockroach-v26.2.4")
)

$ErrorActionPreference = "Stop"
$version = "v26.2.4"
$archiveName = "cockroach-$version.windows-6.2-amd64.zip"
$expectedSha256 = "d35da3f82aba839204823736352ee3df9286b1d27ddd22cbb8568a913df5d1e9"
$downloadUrl = "https://binaries.cockroachdb.com/$archiveName"
$resolvedDestination = [System.IO.Path]::GetFullPath($Destination)
$workspaceRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))

if (-not $resolvedDestination.StartsWith($workspaceRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Destination must remain inside the BoneTwin workspace."
}

$archivePath = Join-Path ([System.IO.Path]::GetTempPath()) $archiveName
$curl = Get-Command "curl.exe" -ErrorAction SilentlyContinue
if ($curl) {
    & $curl.Source --location --continue-at - --silent --show-error --output $archivePath $downloadUrl
    if ($LASTEXITCODE -ne 0) {
        throw "CockroachDB download failed."
    }
}
else {
    Invoke-WebRequest -Uri $downloadUrl -OutFile $archivePath
}
$actualSha256 = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualSha256 -ne $expectedSha256) {
    throw "CockroachDB archive SHA-256 verification failed."
}

New-Item -ItemType Directory -Path $resolvedDestination -Force | Out-Null
Expand-Archive -LiteralPath $archivePath -DestinationPath $resolvedDestination -Force
Remove-Item -LiteralPath $archivePath

$binary = Get-ChildItem -Path $resolvedDestination -Recurse -Filter "cockroach.exe" |
    Select-Object -First 1
if (-not $binary) {
    throw "The verified archive did not contain cockroach.exe."
}

Write-Output $binary.FullName
