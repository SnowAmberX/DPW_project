# Vue3 Frontend

## Install

```bash
cd frontend
npm install
```

## Run

```bash
npm run dev
```

Default URL: http://127.0.0.1:5173

## Backend Endpoint

The app reads timeline data from:

- `GET /api/v1/infections/timeline`

Optional query params:

- `start_date` (YYYY-MM-DD)
- `end_date` (YYYY-MM-DD)
- `step_days` (>= 1)
