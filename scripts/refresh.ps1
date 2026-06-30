$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
python scripts/update_data.py
python scripts/validate_data.py
python scripts/build.py
Write-Host "更新完成：dist\中国半导体与AI算力产业链研究.html"
