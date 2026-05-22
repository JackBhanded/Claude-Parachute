@echo off
REM Run Claude Parachute from this folder without worrying about PATH.
REM Works whether or not it's been pip-installed (adds bundled src to PYTHONPATH).
setlocal
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
python -m claude_parachute %*
endlocal
