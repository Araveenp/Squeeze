@echo off
cd /d "%~dp0"
echo [1/3] Setting up clean build environment...
if not exist ".venv_build\Scripts\python.exe" (
  echo Creating isolated virtual environment to prevent bundling unused libraries...
  py -m venv .venv_build
  if errorlevel 1 goto fail
)

echo Installing required packages...
.\.venv_build\Scripts\python.exe -m pip install -q -r requirements.txt pyinstaller
if errorlevel 1 goto fail

echo [2/3] Building Squeeze.exe...
.\.venv_build\Scripts\pyinstaller.exe --noconfirm --clean --windowed --name Squeeze --icon squeeze.ico app.py
if errorlevel 1 goto fail

echo [3/3] Building the installer...
call :findiscc
if not defined ISCC (
  echo Installing Inno Setup, approve the prompt if Windows asks...
  winget install -e --id JRSoftware.InnoSetup --silent --accept-package-agreements --accept-source-agreements
  call :findiscc
)
if not defined ISCC goto noinno
"%ISCC%" /Q installer.iss
if errorlevel 1 goto fail
echo.
echo Done. Your installer is: %~dp0SqueezeSetup.exe
pause
exit /b 0

:findiscc
set "ISCC="
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
exit /b 0

:noinno
echo Could not install Inno Setup automatically.
echo Get it from https://jrsoftware.org/isdl.php, install it, then run this file again.
echo Meanwhile dist\Squeeze\Squeeze.exe already works on its own.
pause
exit /b 1

:fail
echo Build failed. Scroll up to see the error.
pause
exit /b 1
