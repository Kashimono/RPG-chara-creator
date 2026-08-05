@echo off
REM Run the RPG package using the project virtual environment.
cd /d "%~dp0"
SET VENV_PATH=%~dp0.\.venv\Scripts\python.exe
IF NOT EXIST "%VENV_PATH%" (
    echo Virtual environment not found.
    echo Create it with: python -m venv .venv
    pause
    exit /b 1
)
"%VENV_PATH%" -m RPG
