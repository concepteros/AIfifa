param(
    [string]$Config = ".\data\telegram-panel.example.json",
    [string]$EnvFile = ".\.env"
)

$ErrorActionPreference = "Stop"
$Python = if ($env:PYTHON) { $env:PYTHON } elseif (Test-Path ".\.venv-panel\Scripts\python.exe") { ".\.venv-panel\Scripts\python.exe" } else { "python" }
$env:PYTHONPATH = "src"

& $Python -m predict_odds --env-file $EnvFile telegram-panel --config $Config
