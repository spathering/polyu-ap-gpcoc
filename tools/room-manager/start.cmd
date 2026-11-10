@echo off
setlocal
if exist "%~dp0dist\RoomManager\RoomManager.exe" (
  start "" "%~dp0dist\RoomManager\RoomManager.exe" %*
) else (
  "%~dp0.venv\Scripts\pythonw.exe" "%~dp0manager.py" %*
)
