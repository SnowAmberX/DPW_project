from __future__ import annotations

from pydantic import BaseModel, Field


class TraditionalOnnxForecastRequest(BaseModel):
    origin_country: str = Field(..., min_length=2, description="Clicked country name or ISO-3 code")
    forecast_days: int = Field(default=365, ge=1, le=730, description="How many days to forecast forward")
    step_days: int = Field(default=1, ge=1, le=30, description="Return one frame every N days")
    start_date: str | None = Field(default=None, description="Optional simulation start date in YYYY-MM-DD")
    use_global_fallback_only: bool | None = Field(
        default=None,
        description=(
            "Override runtime mode: True = use global fallback only; False = use per-country models when available. "
            "If omitted, environment variable TRADITIONAL_ONNX_USE_GLOBAL_FALLBACK_ONLY is used."
        ),
    )


class TraditionalOnnxForecastFrame(BaseModel):
    date: str = Field(..., description="Forecast date in YYYY-MM-DD")
    infections_by_country: dict[str, int] = Field(default_factory=dict)


class TraditionalOnnxForecastResponse(BaseModel):
    model_family: str = Field(default="traditional_onnx")
    metric: str = Field(default="predicted_active_cases")
    origin_country_code: str = Field(..., min_length=3, max_length=3)
    origin_country_name: str
    origin_first_case_date: str | None = Field(default=None, description="Historical first-case date of origin country")
    frame_count: int = Field(..., ge=1)
    forecast_days: int = Field(..., ge=1)
    step_days: int = Field(..., ge=1)
    start_date: str = Field(..., description="First frame date in YYYY-MM-DD")
    end_date: str = Field(..., description="Last frame date in YYYY-MM-DD")
    max_infections: int = Field(..., ge=0)
    frames: list[TraditionalOnnxForecastFrame] = Field(default_factory=list)
