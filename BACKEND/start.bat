@echo off
cd /d "%~dp0"
echo Nexura Scanner ishga tushyapti...

if not exist "..\FRONTEND\dist\index.html" (
    echo [i] Frontend build qilinmoqda...
    cd ..\FRONTEND
    call npm ci && call npm run build
    cd ..\BACKEND
)

set PYTHON=python
if exist "..\venv\Scripts\python.exe" set PYTHON=..\venv\Scripts\python.exe

if /i "%1"=="--prod" goto :prod
if /i "%1"=="-p" goto :prod

start /b "" "%PYTHON%" -m nexura web
timeout /t 4 /nobreak >nul
start http://127.0.0.1:8080
echo.
echo Browser: http://127.0.0.1:8080
echo.
echo To'xtatish: taskkill /f /im python.exe
goto :eof

:prod
echo [Production mode]
start /b "" "%PYTHON%" -m uvicorn nexura.web.app:app --host 127.0.0.1 --port 8080 --workers 4 --log-level info
timeout /t 3 /nobreak >nul
echo Server: http://127.0.0.1:8080
echo API:    http://127.0.0.1:8080/api/status
echo.
echo To'xtatish: taskkill /f /im python.exe