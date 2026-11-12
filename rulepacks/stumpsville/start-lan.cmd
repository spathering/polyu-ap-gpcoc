@echo off
setlocal
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONUTF8=1"
set "SV_PYTHONW=%~dp0..\..\engineering\.venv\Scripts\pythonw.exe"
if not exist "%SV_PYTHONW%" (
  echo Python environment not found. Please install project dependencies first.
  pause
  exit /b 1
)
start "" "%SV_PYTHONW%" -B "%~dp0tools\lan.py" %*
