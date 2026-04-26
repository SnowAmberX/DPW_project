# FastAPI Backend

## Run

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## API

- `GET /health`
- `POST /api/v1/infections/snapshot`
- `GET /api/v1/infections/timeline`
- `POST /api/v1/infections/neural-prediction`

Request body example:

```json
{
  "country_code": "CHN"
}
```

Response example:

```json
{
  "time": "2026:04:18",
  "infections_by_country": {
    "CHN": 12345,
    "USA": 45678
  }
}
```

Timeline response example:

```json
{
  "metric": "total_cases",
  "frame_count": 3,
  "start_date": "2020-01-04",
  "end_date": "2020-02-01",
  "max_infections": 12500,
  "frames": [
    {
      "date": "2020-01-04",
      "infections_by_country": {
        "Afghanistan": 0,
        "United States": 0
      }
    }
  ]
}
```

Timeline query params:

- `start_date` (optional, `YYYY-MM-DD`)
- `end_date` (optional, `YYYY-MM-DD`)
- `step_days` (optional, default `7`, range `1~90`)

Neural prediction request body example:

```json
{
  "seed_country": "USA",
  "start_date": "2026-01-01"
}
```

Neural prediction response example (simplified):

```json
{
  "metric": "predicted_new_cases",
  "seed_country_code": "USA",
  "seed_country_name": "United States",
  "frame_count": 60,
  "start_date": "2026-01-01",
  "end_date": "2026-03-01",
  "max_new_cases": 12345.67,
  "frames": [
    {
      "day": 1,
      "date": "2026-01-01",
      "new_cases_by_country": {
        "United States": 12000.12,
        "Japan": 2300.88
      }
    }
  ]
}
```

If your environment does not have neural dependencies, install them from the project root:

```bash
uv pip install -r model/neural/requirements.txt
```
