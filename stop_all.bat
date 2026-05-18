@echo off
setlocal
set ROOT_DIR=%~dp0
echo [stop_all] root: %ROOT_DIR%

echo Stopping frontend (node / vite)...
taskkill /F /IM node.exe >nul 2>&1 || echo node not running

echo Stopping backend (python / uvicorn)...
taskkill /F /IM python.exe >nul 2>&1 || echo python not running

echo Done. Check backend.log and frontend.log for details.
