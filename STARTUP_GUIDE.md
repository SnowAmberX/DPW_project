# Frontend + Backend Startup Guide

This guide explains how to run the Streamlit frontend and FastAPI backend in this project.

## 1. Open Two Terminals

Use two separate terminals:
- Terminal A: backend
- Terminal B: frontend

## 2. Start Backend (FastAPI)

### Step 1: Go to backend folder

```bash
cd /Users/skiwalllee/code/self_project/DPW_project/backend
```

### Step 2: Install backend dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Run backend server

```bash
uvicorn app.main:app --reload --port 8000
```

### Step 4: Verify backend is running

Open in browser:
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs

Expected health response:

```json
{"status":"ok"}
```

## 3. Start Frontend (Streamlit)

### Step 1: Go to project root

```bash
cd /Users/skiwalllee/code/self_project/DPW_project
```

### Step 2: Install frontend dependencies

```bash
pip install streamlit plotly pandas
```

### Step 3: Run frontend app

```bash
streamlit run App/app_test.py
```

## 4. Test Frontend ↔ Backend Connection

1. Keep backend running on port 8000.
2. Open frontend page.
3. In sidebar, keep API URL as:

```text
http://127.0.0.1:8000/api/v1/infections/snapshot
```

4. Click a country on the map.
5. Check backend terminal output. You should see a printed country code, such as:

```text
[backend] country_code received: USA
```

## 5. Common Issues

### Error: No module named uvicorn

Run:

```bash
cd /Users/skiwalllee/code/self_project/DPW_project/backend
pip install -r requirements.txt
```

### Error: Backend connection failed (in Streamlit warning)

Check:
- Backend is running.
- Backend URL in sidebar is correct.
- Port 8000 is not blocked/occupied.

### Error: streamlit command not found

Run:

```bash
pip install streamlit
```

## 6. Stop Services

Press `Ctrl + C` in each terminal.

## 7. Suggested Workflow

1. Start backend first.
2. Confirm `/health` works.
3. Start frontend.
4. Click map countries to test request flow.
