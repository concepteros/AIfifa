param(
    [string]$Config = ".\data\bot-scan.json",
    [string]$Time = "09:00",
    [string]$Timezone = "Asia/Shanghai",
    [string]$EnvFile = ".\.env"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = $env:PYTHON
if (-not $Python) {
    $Python = "python"
}

$env:PYTHONPATH = Join-Path $ProjectRoot "src"
& $Python -m predict_odds --env-file $EnvFile schedule --config $Config --time $Time --timezone $Timezone
