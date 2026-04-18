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
