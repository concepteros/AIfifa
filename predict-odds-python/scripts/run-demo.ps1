param(
    [string]$Output = ".\demo-out"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = $env:PYTHON
if (-not $Python) {
    $Python = "python"
}

$env:PYTHONPATH = Join-Path $ProjectRoot "src"
& $Python -m predict_odds demo --output $Output
