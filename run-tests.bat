@echo off
REM ===========================================================================
REM  Claude Parachute - test runner (just double-click me)
REM
REM  Proves the shadow-git safety net before it ever touches a real project.
REM  Green = the parachute opens. (Needs git installed; tests that need it skip
REM  cleanly if it's missing.)
REM ===========================================================================
setlocal
cd /d "%~dp0"

echo.
echo   Checking the parachute's stitching... (running the safety tests)
echo.

python -m pytest --version >nul 2>&1
if errorlevel 1 (
    echo   First run - fetching the test tool ^(pytest^). One moment...
    python -m pip install --quiet pytest
)

python -m pytest
set RESULT=%errorlevel%

echo.
if "%RESULT%"=="0" (
    echo   All good - the parachute opens clean. :^)
) else (
    echo   Some tests didn't pass. Nothing of yours was touched - these run in a
    echo   scratch folder only. Send me the output above and I'll fix it.
)
echo.
pause
endlocal
