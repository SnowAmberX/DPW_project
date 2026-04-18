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
