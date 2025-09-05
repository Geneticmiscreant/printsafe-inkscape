@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Print-Safe Installer (copy-only v2)

echo.
echo === Print-Safe (CMYK Lock) — copy-only installer ===
echo This script ONLY copies files. It never checks Python.
echo -----------------------------------------------------

rem -- where the installer lives (with the source files)
set "HERE=%~dp0"
set "SRC_PY=%HERE%printsafe.py"
set "SRC_INX=%HERE%printsafe.inx"

if not exist "%SRC_PY%"  (echo ERROR: printsafe.py not found next to this installer.& goto end)
if not exist "%SRC_INX%" (echo ERROR: printsafe.inx not found next to this installer.& goto end)

rem -- user extension locations (both casings; different builds use one or the other)
set "U1=%APPDATA%\Inkscape\extensions"
set "U2=%APPDATA%\inkscape\extensions"

echo.
echo Copying to user extension folders...
for %%D in ("%U1%" "%U2%") do (
  if not exist "%%~D" mkdir "%%~D" >nul 2>&1
  copy /Y "%SRC_PY%"  "%%~D\" >nul && echo  ✓ printsafe.py  -> %%~D
  copy /Y "%SRC_INX%" "%%~D\" >nul && echo  ✓ printsafe.inx -> %%~D
)

rem -- OPTIONAL: also copy to system folder if we are admin (nice-to-have)
set "SYS=C:\Program Files\Inkscape\share\inkscape\extensions"
if exist "%SYS%" (
  echo.
  net session >nul 2>&1
  if %errorlevel%==0 (
    echo Copying to system extensions (admin)...
    copy /Y "%SRC_PY%"  "%SYS%\" >nul && echo  ✓ printsafe.py  -> %SYS%
    copy /Y "%SRC_INX%" "%SYS%\" >nul && echo  ✓ printsafe.inx -> %SYS%
  ) else (
    echo (Not admin; skipping system-wide copy to "%SYS%")
  )
)

rem -- OPTIONAL: install any ICC/ICM profiles found next to installer or in .\icc\
set "ICCDEST=%SystemRoot%\System32\spool\drivers\color"
set COPIEDICC=0
for %%E in (icc icm) do (
  for %%F in ("%HERE%*.%%E") do (copy /Y "%%~fF" "%ICCDEST%\" >nul && set COPIEDICC=1)
  if exist "%HERE%icc\*.%%E" (
    for %%F in ("%HERE%icc\*.%%E") do (copy /Y "%%~fF" "%ICCDEST%\" >nul && set COPIEDICC=1)
  )
)
if "%COPIEDICC%"=="1" (
  echo.
  echo Installed ICC profiles to: %ICCDEST%
)

echo.
echo Done. Restart Inkscape, then check:
echo   Extensions ^> Print ^> Print-Safe (CMYK Lock)
echo If you don't see it, open Preferences ^> System and note the "User extensions" path.
echo -----------------------------------------------------
:end
echo.
pause
