@echo off
title Music Video Equal Time Compiler
color 0A

echo ===============================================
echo    MUSIC VIDEO EQUAL TIME COMPILER
echo ===============================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found! Please install Python first.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python found! Checking dependencies...
echo.

REM Install dependencies
echo Installing required packages...
pip install librosa numpy moviepy tqdm openai-whisper

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install dependencies!
    echo Please check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo ===============================================
echo Dependencies installed successfully!
echo ===============================================
echo.

REM Run the beat sync compiler
echo Starting Music Video Equal Time Compiler...
echo.
python music_video_beat_sync_compiler.py

echo.
echo ===============================================
echo Script execution completed!
echo ===============================================
pause