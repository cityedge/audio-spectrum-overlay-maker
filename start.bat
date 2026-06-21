@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Local Python environment .venv was not found.
  echo Running setup.bat first...
  call setup.bat
  if errorlevel 1 exit /b 1
)

".venv\Scripts\python.exe" app.py
set EXITCODE=%ERRORLEVEL%

if not "%EXITCODE%"=="0" (
  echo.
  echo Application exited with error code: %EXITCODE%
  pause
  exit /b %EXITCODE%
)
