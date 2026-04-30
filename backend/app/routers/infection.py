import logging

from fastapi import APIRouter, HTTPException, Query

from app.schemas.infection import (
    InfectionSnapshotRequest,
    InfectionSnapshotResponse,
    InfectionTimelineResponse,
    NeuralPredictionRequest,
    NeuralPredictionResponse,
)
from app.schemas.traditional_onnx import (
    TraditionalOnnxForecastRequest,
    TraditionalOnnxForecastResponse,
)
from app.services.mock_data import generate_mock_snapshot
from app.services.neural_prediction import build_neural_prediction_timeline
from app.services.timeline_data import build_infection_timeline
from app.services.traditional_onnx.traditional_onnx_forecast_service import (
    forecast_traditional_onnx_global_infections,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/infections", tags=["infections"])


@router.post("/snapshot", response_model=InfectionSnapshotResponse)
def get_infection_snapshot(payload: InfectionSnapshotRequest) -> InfectionSnapshotResponse:
    country_code = payload.country_code.upper()

    # Log incoming country code to verify connectivity.
    print(f"[backend] country_code received: {country_code}")
    logger.info("country_code received: %s", country_code)

    snapshot = generate_mock_snapshot()
    return InfectionSnapshotResponse(**snapshot)


@router.get("/timeline", response_model=InfectionTimelineResponse)
def get_infection_timeline(
    start_date: str | None = Query(default=None, description="Optional start date in YYYY-MM-DD format"),
    end_date: str | None = Query(default=None, description="Optional end date in YYYY-MM-DD format"),
    step_days: int = Query(default=7, ge=1, le=90, description="Sample one frame every N days"),
) -> InfectionTimelineResponse:
    try:
        timeline = build_infection_timeline(start_date=start_date, end_date=end_date, step_days=step_days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return InfectionTimelineResponse(**timeline)


@router.post("/neural-prediction", response_model=NeuralPredictionResponse)
def get_neural_prediction(payload: NeuralPredictionRequest) -> NeuralPredictionResponse:
    try:
        prediction = build_neural_prediction_timeline(
            seed_country=payload.seed_country,
            start_date=payload.start_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return NeuralPredictionResponse(**prediction)


@router.post("/traditional-onnx-forecast", response_model=TraditionalOnnxForecastResponse)
def get_traditional_onnx_forecast(
    payload: TraditionalOnnxForecastRequest,
) -> TraditionalOnnxForecastResponse:
    try:
        forecast = forecast_traditional_onnx_global_infections(
            origin_country=payload.origin_country,
            forecast_days=payload.forecast_days,
            start_date=payload.start_date,
            step_days=payload.step_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return TraditionalOnnxForecastResponse(**forecast)
