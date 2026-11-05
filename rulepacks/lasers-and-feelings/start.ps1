param([int]$Port = 8877)
$ErrorActionPreference = 'Stop'
$packRoot = $PSScriptRoot
$projectRoot = Split-Path (Split-Path $packRoot -Parent) -Parent
$pythonPath = Join-Path $projectRoot 'engineering/.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw '缺少已安装的工程 Python 环境。请按项目工程文档准备运行环境后再启动。'
}
$env:PYTHONDONTWRITEBYTECODE = '1'
& $pythonPath -B (Join-Path $packRoot 'tools/launch.py') --port $Port
exit $LASTEXITCODE
