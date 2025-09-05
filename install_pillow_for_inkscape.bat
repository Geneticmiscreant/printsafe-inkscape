@echo off
setlocal

echo === Install Pillow into Inkscape's bundled Python ===

rem Try common locations; fall back to prompt.
set "PYTHON_EXE="
for %%D in ("%ProgramFiles%\Inkscape\bin" "%ProgramFiles(x86)%\Inkscape\bin") do (
  if exist "%%~D\python3.exe" set "PYTHON_EXE=%%~D\python3.exe"
)

if not defined PYTHON_EXE (
  echo Could not find Inkscape's Python automatically.
  set /p PYTHON_EXE="Enter full path to Inkscape's python3.exe (e.g. C:\Program Files\Inkscape\bin\python3.exe): "
)

if not exist "%PYTHON_EXE%" (
  echo ERROR: "%PYTHON_EXE%" not found.
  pause & exit /b 1
)

echo Using: "%PYTHON_EXE%"
echo.

rem Make sure pip exists, then install/upgrade Pillow for the current user.
"%PYTHON_EXE%" -m pip --version >nul 2>&1 || "%PYTHON_EXE%" -m ensurepip --upgrade
"%PYTHON_EXE%" -m pip install --user --upgrade pillow

if errorlevel 1 (
  echo .
  echo Pillow install FAILED. Check your internet/proxy or try running this as Administrator.
  pause & exit /b 1
) else (
  echo .
  echo Pillow installed OK.
  echo Restart Inkscape and try the extension again.
  pause & exit /b 0
)
