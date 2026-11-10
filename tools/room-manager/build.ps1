$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw '先运行 python -m venv .venv 并按 requirements-build.lock 安装依赖' }
& $python (Join-Path $PSScriptRoot 'build.py')
if ($LASTEXITCODE -ne 0) { throw 'Python 桌面打包失败' }
