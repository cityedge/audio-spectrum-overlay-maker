@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo Audio Spectrum Overlay Maker v1.3.0 setup
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python launcher "py" was not found.
  echo Please install Python 3.10 or later, or enable the Python launcher.
  pause
  exit /b 1
)

set "PYTHON_CMD=py -3"
set "PYTHON_VERSION="
for /f "delims=" %%V in ('%PYTHON_CMD% -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2^>nul') do set "PYTHON_VERSION=%%V"

if not defined PYTHON_VERSION (
  echo ERROR: Python 3 was not found by the Python launcher.
  echo Please install Python 3.10 or later and make sure "py -3" works.
  pause
  exit /b 1
)

%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
  echo ERROR: Python 3.10 or later is required.
  echo Detected Python %PYTHON_VERSION% via "py -3".
  pause
  exit /b 1
)

echo Using Python %PYTHON_VERSION% via "py -3".

set "LOCAL_FFMPEG=%~dp0bin\ffmpeg.exe"
set "LOCAL_FFPROBE=%~dp0bin\ffprobe.exe"

if exist "%LOCAL_FFMPEG%" (
  echo Found local ffmpeg: %LOCAL_FFMPEG%
) else (
  where ffmpeg >nul 2>nul
  if errorlevel 1 (
    echo ERROR: ffmpeg was not found.
    echo Place ffmpeg.exe in the bin folder next to this BAT, or add ffmpeg to PATH.
    pause
    exit /b 1
  )
)

if exist "%LOCAL_FFPROBE%" (
  echo Found local ffprobe: %LOCAL_FFPROBE%
) else (
  where ffprobe >nul 2>nul
  if errorlevel 1 (
    echo ERROR: ffprobe was not found.
    echo Place ffprobe.exe in the bin folder next to this BAT, or add ffprobe to PATH.
    pause
    exit /b 1
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating local Python environment .venv ...
  %PYTHON_CMD% -m venv .venv
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
