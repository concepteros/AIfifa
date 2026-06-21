param(
    [string]$Config = ".\data\bot-scan.json",
    [string]$Mode = "scan",
    [string]$EnvFile = ".\.env",
    [switch]$WithNetwork
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = $env:PYTHON
if (-not $Python) {
    $Python = "python"
}

$env:PYTHONPATH = Join-Path $ProjectRoot "src"
if ($WithNetwork) {
    & $Python -m predict_odds --env-file $EnvFile doctor --config $Config --mode $Mode
} else {
    & $Python -m predict_odds --env-file $EnvFile doctor --config $Config --mode $Mode --skip-network
}
