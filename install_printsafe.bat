@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Print-Safe Installer

echo === Print-Safe (CMYK Lock) — installer ===

rem --- Where this installer lives (with printsafe.py/.inx)
set "SRC=%~dp0"
set "SRC_PY=%SRC%printsafe.py"
set "SRC_INX=%SRC%printsafe.inx"

if not exist "%SRC_PY%"  ( echo [ERROR] printsafe.py not found next to this installer: %SRC% & goto end )
if not exist "%SRC_INX%" ( echo [ERROR] printsafe.inx not found next to this installer: %SRC% & goto end )

rem --- Locate inkscape.exe (common dirs, then PATH)
set "INK_EXE="
for %%P in (
  "%ProgramFiles%\Inkscape\bin\inkscape.exe"
  "%ProgramFiles(x86)%\Inkscape\bin\inkscape.exe"
  "%LocalAppData%\Programs\Inkscape\bin\inkscape.exe"
) do (
  if exist "%%~P" set "INK_EXE=%%~fP"
)
if not defined INK_EXE (
  for /f "delims=" %%W in ('where inkscape 2^>nul') do set "INK_EXE=%%~fW"
)

if defined INK_EXE (
  echo Found Inkscape: "%INK_EXE%"
  for %%A in ("%INK_EXE%\..") do set "INK_BIN=%%~fA"
  for %%A in ("%INK_BIN%\..") do set "INK_ROOT=%%~fA"
  set "EXT_SYS=%INK_ROOT%\share\inkscape\extensions"
  set "PY=%INK_BIN%\python3.exe"
  if not exist "%PY%" set "PY=%INK_BIN%\python.exe"
) else (
  echo [WARN] Could not auto-locate inkscape.exe. System-copy and Pillow steps may be skipped.
)

rem --- User extension folders (both casings used by different builds)
set "USR1=%APPDATA%\inkscape\extensions"
set "USR2=%APPDATA%\Inkscape\extensions"
for %%D in ("%USR1%" "%USR2%") do if not exist "%%~D" mkdir "%%~D" >nul 2>&1

echo.
echo --- Copying to user extension folders ---
for %%D in ("%USR1%" "%USR2%") do (
  echo -> %%~D
  copy /Y "%SRC_PY%"  "%%~D\" >nul & if exist "%%~D\printsafe.py"  (echo    ok: printsafe.py)  else (echo    !! missing printsafe.py)
  copy /Y "%SRC_INX%" "%%~D\" >nul & if exist "%%~D\printsafe.inx" (echo    ok: printsafe.inx) else (echo    !! missing printsafe.inx)
)

rem --- Try system extension folder (admin not required, but may fail)
if defined EXT_SYS (
  echo.
  echo --- Copying to system extensions (best effort) ---
  echo -> %EXT_SYS%
  copy /Y "%SRC_PY%"  "%EXT_SYS%\" >nul && echo    copied printsafe.py   || echo    (no permission?)
  copy /Y "%SRC_INX%" "%EXT_SYS%\" >nul && echo    copied printsafe.inx  || echo    (no permission?)
)

rem --- Optional: install Pillow into Inkscape's Python if we can find it
if exist "%PY%" (
  echo.
  echo --- Checking Pillow in Inkscape's Python ---
  "%PY%" -c "import PIL, PIL.ImageCms" >nul 2>&1 && (
    echo    Pillow already available
  ) || (
    echo    Installing Pillow...
    "%PY%" -m pip --version >nul 2>&1 || "%PY%" -m ensurepip --upgrade
    "%PY%" -m pip install pillow
  )
) else (
  echo.
  echo [NOTE] Inkscape's Python not found; skipping Pillow install (extension may still work).
)

rem --- Optional: install ICC profiles (from next to installer or .\icc\)
set "ICCDEST=%SystemRoot%\System32\spool\drivers\color"
set COPIEDICC=0
for %%E in (icc icm) do (
  for %%F in ("%SRC%*.%%E") do (copy /Y "%%~fF" "%ICCDEST%\" >nul && set COPIEDICC=1)
  if exist "%SRC%icc\*.%%E" (
    for %%F in ("%SRC%icc\*.%%E") do (copy /Y "%%~fF" "%ICCDEST%\" >nul && set COPIEDICC=1)
  )
)
if "%COPIEDICC%"=="1" (
  echo.
  echo Installed ICC profiles to: %ICCDEST%
)

echo.
echo === Done. Restart Inkscape. Menu:  Extensions ^> Print ^> Print-Safe (CMYK Lock)
echo If not visible, open Preferences ^> System and check "User extensions" path.
:end
echo.
pause
