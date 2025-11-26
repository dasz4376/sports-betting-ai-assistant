@echo off
echo.
echo ========================================
echo   NFL BETTING AI - FULL STACK STARTUP
echo ========================================
echo.

echo Starting Backend Server...
cd backend
start cmd /k "py -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo.
echo Starting Frontend Server...
cd ..\frontend
start cmd /k "npm run dev"

echo.
echo ========================================
echo   SERVERS STARTING!
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Press any key to close this window...
pause >nul

