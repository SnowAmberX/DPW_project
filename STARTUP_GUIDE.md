# Frontend + Backend Startup Guide

This guide explains how to run the Vue3 frontend and FastAPI backend in this project.

## 1. Open Two Terminals

Use two terminals:
- Terminal A: backend
- Terminal B: frontend

## 2. Start Backend (FastAPI)

### Step 1: Enter backend directory

```bash
cd backend
```

### Step 2: Install backend dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Run backend server

```bash
uvicorn app.main:app --reload --port 8000
```

### Step 4: Verify backend

Open:
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs

Expected health response:

```json
{"status":"ok"}
```

## 3. Start Frontend (Vue3)

### Step 1: Enter frontend directory

```bash
cd frontend
```

### Step 2: Install frontend dependencies

```bash
npm install
```

### Step 3: Run dev server

```bash
npm run dev
```

Open the frontend URL shown in terminal (default is `http://127.0.0.1:5173`).

## 4. Test Timeline Map Animation

1. Keep backend running on port 8000.
2. Open the Vue page.
3. Ensure Backend URL is `http://127.0.0.1:8000`.
4. Click "重新加载" to fetch timeline data.
5. Click "播放" to animate infection spread by date.

Backend timeline endpoint used by frontend:

```text
GET /api/v1/infections/timeline?start_date=2020-01-04&end_date=2023-12-31&step_days=14
```

## 5. Common Issues

### Error: `No module named uvicorn`

```bash
cd backend
pip install -r requirements.txt
```

### Error: frontend cannot connect backend

Check:
- Backend is running on port 8000.
- Frontend Backend URL is correct.
- CORS is enabled (already configured in `app/main.py`).

### Error: `npm` command not found

Install Node.js LTS, then run:

```bash
npm -v
node -v
```

## 6. Stop Services

Press `Ctrl + C` in both terminals.

## 7. Suggested Workflow

1. Start backend first.
2. Confirm `/health` works.
3. Start frontend.
4. Load timeline and play animation.
