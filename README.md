# DPW_project

This repository implements a data-driven visualization and forecasting demonstration application. Key features:

- Data preprocessing and panel data preparation (data/)
- Backend API (FastAPI) exposing health and infection/timeline endpoints (backend/)
- Frontend visualization (Vue 3 + ECharts) with map animations and interactive controls (frontend/)

Directory overview:

- backend/: FastAPI service and backend logic
- frontend/: Vue 3 + Vite frontend app
- data/: raw and processed datasets
- model/: training scripts and model artifacts

This README includes:

1. Project overview and architecture
2. One‑click start scripts (cross-platform)
3. Manual installation and run steps (Python `.venv`, Node/Vue)
4. Cross-platform notes (macOS / Linux / Windows)
5. Troubleshooting

Purpose

The project demonstrates the full flow from raw epidemic data to interactive timeline visualization and simple forecasting: data cleaning → model/training → service → frontend visualization. It is suitable for teaching, demos, and rapid iteration.

Tech stack

- Backend: Python 3.10+ with FastAPI and Uvicorn
- Frontend: Vue 3 (Vite) and ECharts
- Environments: Python virtual environment `.venv` (recommended) and Node.js + npm

One‑click start (recommended)

Three cross-platform scripts are provided in the repository root:

- [start_all.sh](start_all.sh) — macOS / Linux
- [start_all.ps1](start_all.ps1) — Windows PowerShell

These scripts assume Python and Node.js/npm are installed. See "Manual installation" below if they are not.

Examples

macOS / Linux:

```bash
./start_all.sh
```

Windows PowerShell:

```powershell
.\start_all.ps1
```


What the scripts do:

- Create/activate a Python `.venv` in `backend/` and install backend dependencies
- Run `npm install` in `frontend/` to install frontend dependencies
- Start the backend (uvicorn) and the frontend (Vite dev server)

Manual install and run (step by step)

Follow these steps if you prefer manual control, covering macOS / Linux / Windows.

1) Install system prerequisites

- macOS: install Homebrew (https://brew.sh/) then:

```bash
brew install python node
```

- Ubuntu / Debian:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nodejs npm
```

- Windows: install Python (check "Add to PATH") and Node.js from the official websites, or use package managers (Chocolatey/Scoop/winget).

2) Backend (Python) — create and activate local `.venv`, install dependencies

macOS / Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
cd backend
python -m venv .venv
. .venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
```

Windows (CMD):

```cmd
cd backend
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -U pip
pip install -r requirements.txt
```

Start the backend (while the venv is active):

```bash
uvicorn app.main:app --reload --port 8000
```

3) Frontend (Vue) — install dependencies and start

Make sure Node.js and npm are installed.

```bash
cd frontend
npm install
npm run dev
```

The frontend typically serves at `http://localhost:5173` (Vite default). The backend API listens at `http://127.0.0.1:8000`.

Cross-platform notes

- Windows: PowerShell may restrict script execution (ExecutionPolicy). To allow running the PowerShell script, open an elevated PowerShell and run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

- macOS / Linux: make the shell script executable:

```bash
chmod +x start_all.sh
```

Files added

- [start_all.sh](start_all.sh) — macOS / Linux starter
- [start_all.ps1](start_all.ps1) — PowerShell starter
- [start_all.bat](start_all.bat) — CMD starter

Troubleshooting

- If the frontend cannot reach the backend, confirm the front-end config variable `VITE_BACKEND_BASE_URL` points to `http://127.0.0.1:8000`.
- If Python dependency installation fails, try upgrading pip: `python -m pip install -U pip`.
- If ports are in use, check for other services occupying ports `8000` (backend) or `5173` (frontend).

Next steps

I can run a local environment check (verify Python, Node, npm) or perform a dry-run of the start scripts to validate them. Tell me which you prefer.
