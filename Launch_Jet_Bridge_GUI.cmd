@echo off
setlocal
cd /d "%~dp0"
if defined JETBRIDGE_GUI_PYTHON (
    "%JETBRIDGE_GUI_PYTHON%" "%~dp0launch_gui.py"
) else if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
    "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" "%~dp0launch_gui.py"
) else (
    py -3 "%~dp0launch_gui.py"
)
if errorlevel 1 pause
