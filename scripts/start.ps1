$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
Start-Process python -ArgumentList @('-m', 'openclerk.cli', 'demo')
python -m openclerk.cli serve @args
