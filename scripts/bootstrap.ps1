$ErrorActionPreference = "Stop"
if (-not (Test-Path .venv)) { python -m venv .venv }
& ./.venv/Scripts/python.exe -m pip install --upgrade pip
& ./.venv/Scripts/python.exe -m pip install -e ".[dev]"
Write-Output "Bootstrap complete. No cloud credentials were used."
