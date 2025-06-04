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
    timeout /t 2 /nobreak >nul
)

echo Starting SwarmAI service...
start "SwarmAI" python -m uvicorn app.main:app --host 0.0.0.0 --port 8002

echo.
echo Waiting for service to start...
timeout /t 15 /nobreak >nul

REM Test if service is responding
python -c "import requests; r = requests.get('http://localhost:8002/health', timeout=5); print('Service is running!' if r.status_code == 200 else 'Service failed to start')" 2>nul
if %errorlevel% equ 0 (
    echo.
    echo SUCCESS: SwarmAI is running on http://localhost:8002
    echo Health: http://localhost:8002/health
    echo Models: http://localhost:8002/models
) else (
    echo.
    echo WARNING: Service may still be starting up
    echo Check manually: http://localhost:8002/health
)

echo.
echo Boot complete!
pause 