$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$python = Join-Path $root 'engineering/.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw '缺少工程运行环境，请先安装工程依赖。' }
& $python -B (Join-Path $PSScriptRoot 'tools/launch.py') @args
