$ErrorActionPreference = "Stop"
$python = if (Test-Path .venv/Scripts/python.exe) { ".venv/Scripts/python.exe" } else { "python" }
$env:PYTHONPATH = "src"
& $python -m pytest -q
