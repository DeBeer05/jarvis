@echo off
setlocal
powershell.exe -NoProfile -File "%~dp0scripts\Connect-Google.ps1"
set "JarvisGoogleExit=%errorlevel%"
echo.
pause
exit /b %JarvisGoogleExit%
