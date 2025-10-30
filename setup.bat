@echo off
REM EFA Juxtaposition Analysis - Quick Setup Script for Windows
REM Copyright (C) 2025 John-Are Hansen
REM Licensed under GPL v3.0

echo =========================================
echo EFA Juxtaposition Analysis Setup
echo =========================================
echo.

REM Check if uv is installed
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Error: uv is not installed
    echo.
    echo Please install uv first:
    echo   winget install --id=astral-sh.uv -e
    echo.
    echo Then restart your command prompt and run this script again.
    pause
    exit /b 1
)

echo ✅ uv is installed
for /f "tokens=*" %%i in ('uv --version 2^>nul') do echo   Version: %%i

echo.
echo 📦 Installing dependencies...
uv sync

echo.
echo 🪟 Installing Windows-specific dependencies...
uv add --optional windows

echo.
echo ✅ Setup complete!
echo.
echo To run the application:
echo   uv run python efa_juxtaposition_app/EFA_juxtaposition_v0p9p6.py
echo.
echo Or use the provided batch launchers:
echo   - EFA_juxtaposition_launcher.bat
echo   - EFA_juxtaposition_launcher_advanced.bat
echo.
pause