param(
    [int]$Port = 8899,
    [string]$Bind = '127.0.0.1',
    [string]$DataDir = '',
    [switch]$NoBrowser
)
# Keep this file UTF-8 with BOM for Windows PowerShell 5.1.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$pythonPath = Join-Path $projectRoot 'engineering/.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw '请先按工程文档准备 Python 运行环境。' }
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'
$launchArgs = @('-B', (Join-Path $PSScriptRoot 'tools/launch.py'), '--port', $Port, '--bind', $Bind)
if ($DataDir) { $launchArgs += @('--data-dir', $DataDir) }
if ($NoBrowser) { $launchArgs += '--no-browser' }
& $pythonPath @launchArgs
exit $LASTEXITCODE
