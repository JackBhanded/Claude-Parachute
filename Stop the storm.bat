@echo off
REM Double-click me if Claude Parachute keeps re-opening.
REM Removes only Parachute's snapshot hooks from your Claude settings (with a backup).
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py "stop-the-storm.py"
    goto done
)

where python >nul 2>nul
if %errorlevel%==0 (
    python "stop-the-storm.py"
    goto done
)

echo.
echo   Couldn't find Python on this PC.
echo   Install it from https://www.python.org/downloads/ then double-click me again.
echo.

:done
echo.
pause
