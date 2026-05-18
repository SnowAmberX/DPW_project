# PowerShell one‑click starter script.
# Run in PowerShell (admin or regular user). If ExecutionPolicy blocks scripts, see README.
#>
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Write-Host "[start_all.ps1] root: $root"

$step = "init"
try {
    $step = 'check_python'
    Write-Host "[start_all.ps1] Step: $step - verifying Python"
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "Python is not installed or not in PATH."
    }

    $step = 'create_venv'
    Set-Location "$root\backend"
    if (-not (Test-Path .venv)) {
        Write-Host "[start_all.ps1] Step: $step - creating .venv"
        python -m venv .venv
    }

    $step = 'activate_venv'
    & .\.venv\Scripts\Activate.ps1
    $step = 'pip_update'
    Write-Host "[start_all.ps1] Step: $step - upgrading pip and installing Python deps"
    python -m pip install -U pip
    if (Test-Path requirements.txt) {
        Write-Host "[start_all.ps1] Installing dependencies from requirements.txt (this may take a few minutes for torch/torch-geometric)..."
        if (-not ($?)) {
            throw "Failed to install Python dependencies. If you see errors about torch or torch-geometric, try installing them separately: pip install torch && pip install torch-geometric"
        }
        pip install -r requirements.txt
    }

    $step = 'check_npm'
    Set-Location "$root\frontend"
    Write-Host "[start_all.ps1] Step: $step - verifying npm"
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw "npm is not installed or not in PATH."
    }

    $step = 'npm_install'
    Write-Host "[start_all.ps1] Step: $step - installing npm dependencies"
    npm install

    # detect frontend port (vite.config.js), default 5173
    $frontendPort = 5173
    $viteConfig = Join-Path $root 'frontend\vite.config.js'
    if (Test-Path $viteConfig) {
        $content = Get-Content $viteConfig -Raw
        if ($content -match 'port\s*:\s*([0-9]+)') { $frontendPort = [int]$matches[1] }
    }

    $step = 'start_backend'
    Write-Host "[start_all.ps1] Step: $step - starting backend on port 8000"
    Start-Process -FilePath powershell -ArgumentList '-NoExit','-Command',"cd '$root\\backend'; . .venv\\Scripts\\Activate.ps1; uvicorn app.main:app --reload --port 8000" -WindowStyle Normal

    Start-Sleep -Seconds 1
    # optional check port
    if (Get-Command Test-NetConnection -ErrorAction SilentlyContinue) {
        if (Test-NetConnection -ComputerName '127.0.0.1' -Port 8000 -InformationLevel Quiet) {
            Write-Host "[start_all.ps1] Backend appears to be listening on port 8000"
        } else {
            Write-Host "[start_all.ps1] Warning: backend may not yet be listening on port 8000. Check backend.log"
        }
    }

    $step = 'start_frontend'
    Write-Host "[start_all.ps1] Step: $step - starting frontend (Vite) on port $frontendPort"
    Start-Process -FilePath powershell -ArgumentList '-NoExit','-Command',"cd '$root\\frontend'; npm run dev" -WindowStyle Normal

    Start-Sleep -Seconds 1
    if (Get-Command Test-NetConnection -ErrorAction SilentlyContinue) {
        if (Test-NetConnection -ComputerName '127.0.0.1' -Port $frontendPort -InformationLevel Quiet) {
            Write-Host "[start_all.ps1] Frontend appears to be listening on port $frontendPort"
        } else {
            Write-Host "[start_all.ps1] Warning: frontend may not yet be listening on port $frontendPort. Check frontend.log"
        }
    }

    Write-Host "[start_all.ps1] Started: backend -> http://127.0.0.1:8000 ; frontend -> http://localhost:$frontendPort"

} catch {
    Write-Host "[start_all.ps1] ERROR at step: $step`n$($_.Exception.Message)"
    Write-Host "Check backend.log and frontend.log for details."
    exit 1
}
