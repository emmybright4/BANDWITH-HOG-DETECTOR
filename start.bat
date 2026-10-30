@echo off
title Bandwidth Hog Detector Web Dashboard
color 0A

echo ========================================
echo   BANDWIDTH HOG DETECTOR - WEB DASHBOARD
echo ========================================
echo.

:: Check if running as admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Warning: Not running as Administrator!
    echo    Packet capture may not work.
    echo    Right-click and select "Run as Administrator" for full functionality.
    echo.
    choice /c YN /m "Continue anyway?"
    if errorlevel 2 exit /b
)

:: Check if virtual environment exists
if not exist venv\ (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment
call venv\Scripts\activate

:: Install requirements if needed
echo Installing/updating requirements...
pip install -q --upgrade pip
pip install -q flask flask-socketio flask-cors psutil

:: Start the server
echo.
echo Starting Bandwidth Hog Detector Web Dashboard...
echo.
echo 🌐 Dashboard will open in your browser shortly...
echo 📡 Press Ctrl+C to stop
echo.

:: Open browser after a short delay
timeout /t 3 /nobreak >nul
start http://localhost:5000

:: Run the server
python backend/app.py

pause