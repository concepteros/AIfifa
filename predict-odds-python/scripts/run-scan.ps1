param(
    [string]$Config = ".\data\bot-scan.json",
    [string]$EnvFile = ".\.env"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = $env:PYTHON
if (-not $Python) {
    $Python = "python"
}

$env:PYTHONPATH = Join-Path $ProjectRoot "src"
& $Python -m predict_odds --env-file $EnvFile scan --config $Config
