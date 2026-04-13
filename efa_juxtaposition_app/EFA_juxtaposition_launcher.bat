@echo off
REM EFA Juxtaposition Analysis Launcher
REM Author: John-Are Hansen
REM Copyright (C) 2025 Equinor ASA
REM Licensed under the MIT License

echo ================================
echo EFA Juxtaposition Analysis Launcher
echo ================================
echo.

REM Set the application directory to the parent folder (project root)
cd /d "%~dp0.."
set APP_DIR=%cd%

REM Check if uv is installed
echo [1/6] Checking if uv is installed...
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: uv is not installed or not in PATH
    echo Please install uv using: winget install --id=astral-sh.uv -e
    echo.
    pause
    exit /b 1
)
echo ✓ uv is installed

REM Check if application directory exists
echo [2/6] Checking application directory...
if not exist "%APP_DIR%" (
    echo ERROR: Application directory does not exist: %APP_DIR%
    echo Please create the directory and install the application
    echo.
    pause
    exit /b 1
)
echo ✓ Application directory exists: %APP_DIR%

REM Check if Python application file exists
echo [3/6] Checking for Python application file...
if not exist "%APP_DIR%\efa_juxtaposition_app\EFA_juxtaposition_app.py" (
    echo ERROR: Python application file not found: %APP_DIR%\efa_juxtaposition_app\EFA_juxtaposition_app.py
    echo Please ensure the application file is in the efa_juxtaposition_app subfolder
    echo.
    pause
    exit /b 1
)
echo ✓ Python application file found

REM Check if pyproject.toml exists (uv project file)
echo [4/6] Checking for uv project configuration...
if not exist "%APP_DIR%\pyproject.toml" (
    echo ERROR: uv project configuration not found: %APP_DIR%\pyproject.toml
    echo This suggests the application was not properly initialized with uv
    echo Please run: uv init efa_juxtaposition_analysis in c:\Appl\
    echo.
    pause
    exit /b 1
)
echo ✓ uv project configuration found

REM Check if required dependencies are installed
echo [5/6] Checking Python dependencies...
cd /d "%APP_DIR%"

REM Create a temporary Python script to check imports
echo import sys > check_deps.py
echo try: >> check_deps.py
echo     import numpy, pandas, matplotlib, scipy, shapely >> check_deps.py
echo     print("All required libraries are available") >> check_deps.py
echo except ImportError as e: >> check_deps.py
echo     print(f"Missing library: {e}") >> check_deps.py
echo     sys.exit(1) >> check_deps.py

REM Run the dependency check
uv run check_deps.py >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Required Python libraries are missing
    echo Please install dependencies using: uv add numpy pandas matplotlib scipy shapely
    echo.
    del check_deps.py >nul 2>&1
    pause
    exit /b 1
)
del check_deps.py >nul 2>&1
echo ✓ All required Python libraries are installed

REM Launch the application
echo [6/6] Launching EFA Juxtaposition Analysis...
echo.
echo Starting application... (this may take a few moments)
echo To close the application, close the GUI window or press Ctrl+C in this terminal
echo.

uv run efa_juxtaposition_app/EFA_juxtaposition_app.py

REM Check if the application started successfully
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Application failed to start (exit code: %errorlevel%)
    echo Please check the error messages above
    echo.
    pause
    exit /b 1
)

echo.
echo Application closed successfully
pause