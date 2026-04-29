# AGENTS.md

Agent instructions for this repository. Keep changes minimal, validate locally, and follow existing module boundaries.

## 1) Read First (link, do not duplicate)

- Project overview: [README.md](README.md)
- End-to-end startup flow: [STARTUP_GUIDE.md](STARTUP_GUIDE.md)
- Backend API contract: [backend/README.md](backend/README.md)
- Frontend setup and API usage: [frontend/README.md](frontend/README.md)
- Model strategy context: [model/model_selection_plan.txt](model/model_selection_plan.txt)

## 2) Quick Start Commands

From repository root:

- Backend (FastAPI)
  - `cd backend`
  - `pip install -r requirements.txt`
  - `uvicorn app.main:app --reload --port 8000`
- Frontend (Vue + Vite)
  - `cd frontend`
  - `npm install`
  - `npm run dev`
- Model training (LightGBM -> ONNX artifacts)
  - `cd model`
  - `pip install -r requirements.txt`
  - `python train_lightgbm_country_models_v4_simple.py`
- Streamlit test app (optional)
  - `cd App`
  - `streamlit run app_test.py`

## 3) Architecture Boundaries

- `backend/app/routers/`: HTTP layer only (validation, request/response, status codes).
- `backend/app/services/`: data loading and forecasting logic.
- `backend/app/constants/traditional_onnx_paths.py`: canonical paths for model/data artifacts.
- `frontend/src/api/infection.js`: frontend API client; keep request shapes aligned with backend schemas.
- `frontend/src/App.vue`: visualization and interaction logic.
- `data/data_processing/`: data preparation scripts.
- `model/`: training pipeline and artifact generation.

## 4) Critical Data and Artifact Prerequisites

- Timeline endpoint depends on:
  - `data/processed_data/cleaned_cases_deaths.csv`
- Traditional ONNX forecast depends on:
  - `model/model/artifacts_country_v4_simple/model_registry.json`
  - `data/processed_data/cleaned_panel_country_day.csv`
  - `data/processed_data/cleaned_cases_deaths.csv`

If these files are missing, run data processing and/or model training before debugging API behavior.

## 5) API and Frontend Integration Rules

- Backend base URL defaults to `http://127.0.0.1:8000` in frontend API client.
- Override with `VITE_BACKEND_BASE_URL` when needed.
- Keep parameter names stable (`start_date`, `end_date`, `step_days`, `origin_country`, `forecast_days`).
- Date input format is `YYYY-MM-DD`.
- For Vue click handlers, avoid accidentally passing DOM event objects when a method expects domain values.

## 6) Validation Checklist After Changes

- Backend changes:
  - Verify `GET /health` returns OK.
  - Verify changed endpoint via `http://127.0.0.1:8000/docs`.
- Frontend changes:
  - Confirm map loads and requests succeed against running backend.
  - Confirm origin-country interactions still trigger forecast requests.
- Model/data pipeline changes:
  - Confirm expected processed files and ONNX artifacts are regenerated in the paths above.

## 7) Repo Conventions for Agents

- Prefer small, focused edits over broad refactors.
- Do not rename API fields unless both backend schemas and frontend client are updated together.
- Keep path-sensitive logic centralized in constants/modules already used by the codebase.
- When updating instructions/docs, add links to canonical docs instead of duplicating long explanations.
