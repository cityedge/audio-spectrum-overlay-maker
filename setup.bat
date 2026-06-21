@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo Audio Spectrum Overlay Maker v1.0.0 setup
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python launcher "py" was not found.
  echo Please install Python 3.10 or later, or enable the Python launcher.
  pause
  exit /b 1
)

where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo ERROR: ffmpeg was not found in PATH.
  echo Please install ffmpeg and add it to PATH.
  pause
  exit /b 1
)

where ffprobe >nul 2>nul
if errorlevel 1 (
  echo ERROR: ffprobe was not found in PATH.
  echo ffprobe is included with ffmpeg. Please add the ffmpeg folder to PATH.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating local Python environment .venv ...
  py -m venv .venv
  if errorlevel 1 (
    echo ERROR: Failed to create .venv.
    pause
    exit /b 1
  )
)

echo Installing required packages...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  echo ERROR: pip upgrade failed.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo ERROR: package installation failed.
  pause
  exit /b 1
)

echo.
echo Setup completed.
pause
