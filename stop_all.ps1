<#
  stop_all.ps1
  Stops backend (uvicorn/python) and frontend (node/vite) on Windows PowerShell.
#>
$ErrorActionPreference = 'SilentlyContinue'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Write-Output "[stop_all] root: $Root"

Write-Output "Stopping frontend (node/vite / npm)..."
# Stop processes whose command line mentions vite or npm run dev
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'vite' -or $_.CommandLine -match 'npm run dev' -or $_.CommandLine -match 'npm' } | ForEach-Object {
    Write-Output "Stopping PID: $($_.ProcessId) ($($_.Name))"
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

Write-Output "Stopping backend (uvicorn / python)..."
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'uvicorn' -or $_.CommandLine -match 'app.main:app' -or $_.Name -match 'python' } | ForEach-Object {
    Write-Output "Stopping PID: $($_.ProcessId) ($($_.Name))"
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

Write-Output "Done. Check backend.log and frontend.log for details."
