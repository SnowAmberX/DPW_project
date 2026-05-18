@echo off
REM Windows CMD one‑click starter script
chcp 65001 >nul
SET ROOT_DIR=%~dp0
echo [start_all.bat] root: %ROOT_DIR%
set STEP=init

echo Step: %STEP% - preparing backend
cd /d "%ROOT_DIR%backend"
where python >nul 2>&1 || (echo Python not found, please install Python. & goto :EOF)
if not exist .venv (
    echo Creating virtualenv (.venv)
    python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -U pip
if exist requirements.txt (
    echo Installing dependencies from requirements.txt ^(this may take a few minutes for torch/torch-geometric^)...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install Python dependencies. If you see errors about torch or torch-geometric, try installing them separately:
        echo   pip install torch
        echo   pip install torch-geometric
        pause
        goto :EOF
    )
)

echo Step: checking npm and installing frontend deps
cd /d "%ROOT_DIR%frontend"
where npm >nul 2>&1 || (echo npm not found, please install Node.js/npm. & goto :EOF)
call npm install

rem detect frontend port from vite.config.js (fallback 5173)
set FRONTEND_PORT=5173
if exist "%ROOT_DIR%frontend\vite.config.js" (
    for /f "tokens=2 delims=:" %%p in ('findstr /R "port *: *[0-9][0-9]*" "%ROOT_DIR%frontend\vite.config.js"') do (
        set PORT_TOKEN=%%p
    )
    if defined PORT_TOKEN (
        for /f "tokens=*" %%q in ("%PORT_TOKEN%") do set FRONTEND_PORT=%%q
        rem trim spaces
        for /f "tokens=* delims= " %%r in ("%FRONTEND_PORT%") do set FRONTEND_PORT=%%r
    )
)

echo Starting backend and frontend...
start "Backend" cmd /k "cd /d ""%ROOT_DIR%backend"" && call .venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"
start "Frontend" cmd /k "cd /d ""%ROOT_DIR%frontend"" && npm run dev"

echo Started: backend -> http://127.0.0.1:8000 ; frontend -> http://localhost:%FRONTEND_PORT%
exit /b 0
