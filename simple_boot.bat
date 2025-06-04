@echo off
echo.
echo Starting SwarmAI Router 2.0 on port 8002...
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found
    pause
    exit /b 1
)

REM Check if port 8002 is free
netstat -an | findstr ":8002 " >nul 2>&1
if %errorlevel% equ 0 (
    echo Port 8002 is in use. Stopping existing service...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8002 "') do (
        if "%%a" neq "0" (
            taskkill /PID %%a /F >nul 2>&1
        )
    )
    timeout /t 3 /nobreak >nul
)

echo Starting SwarmAI service...
start "SwarmAI" python -m uvicorn app.main:app --host 127.0.0.1 --port 8002

echo.
echo Waiting for service to start...
timeout /t 20 /nobreak >nul

REM Test if service is responding with curl (more reliable than requests)
curl -s http://127.0.0.1:8002/health >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo SUCCESS: SwarmAI is running on http://127.0.0.1:8002
    echo Health: http://127.0.0.1:8002/health
    echo Models: http://127.0.0.1:8002/models
    echo API Docs: http://127.0.0.1:8002/docs
) else (
    REM Fallback to netstat check if curl isn't available
    netstat -an | findstr ":8002 " >nul 2>&1
    if %errorlevel% equ 0 (
        echo.
        echo SUCCESS: SwarmAI service started on port 8002
        echo Health: http://127.0.0.1:8002/health
        echo Models: http://127.0.0.1:8002/models
        echo API Docs: http://127.0.0.1:8002/docs
    ) else (
        echo.
        echo WARNING: Service may have failed to start
        echo Check the SwarmAI window for errors
        echo Manual check: http://127.0.0.1:8002/health
    )
)

echo.
echo Boot complete! The service should be running in a separate window.
pause 