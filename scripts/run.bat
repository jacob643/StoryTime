@echo off
REM Story Time launcher — tries PyInstaller binary first, falls back to python -m backend.main

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."

if exist "%PROJECT_DIR%\dist\StoryTime\StoryTime.exe" (
    title Story Time
    "%PROJECT_DIR%\dist\StoryTime\StoryTime.exe"
    exit /b
)

if exist "%PROJECT_DIR%\dist\StoryTime.exe" (
    title Story Time
    "%PROJECT_DIR%\dist\StoryTime.exe"
    exit /b
)

echo [storytime] PyInstaller binary not found, starting via python...
cd /d "%PROJECT_DIR%"
python -m backend.main
