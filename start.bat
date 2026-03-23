@echo off
:: ─────────────────────────────────────────────────────────────
::  X Bulk Blocker — one-click launcher (Windows)
::  Double-click this file to start
:: ─────────────────────────────────────────────────────────────

where docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo  X  Docker is not installed.
    echo     Download Docker Desktop from https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)

echo Building and starting X Bulk Blocker...
docker compose up --build -d

echo.
echo  Done!  Opening http://localhost:7070 ...
timeout /t 2 /nobreak >nul
start http://localhost:7070

echo.
echo  To stop:  docker compose down
pause
