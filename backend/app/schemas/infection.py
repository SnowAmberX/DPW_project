from pydantic import BaseModel, Field


class InfectionSnapshotRequest(BaseModel):
    country_code: str = Field(..., min_length=3, max_length=3, description="ISO-3 country code from frontend click")


class InfectionSnapshotResponse(BaseModel):
    time: str = Field(..., description="Date string in YYYY:MM:DD format")
    infections_by_country: dict[str, int]


class InfectionTimelineFrame(BaseModel):
    date: str = Field(..., description="Date string in YYYY-MM-DD format")
    infections_by_country: dict[str, int] = Field(default_factory=dict)


class InfectionTimelineResponse(BaseModel):
    metric: str = Field(default="total_cases", description="Metric used to build timeline")
    frame_count: int = Field(..., ge=1)
    start_date: str = Field(..., description="Timeline start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="Timeline end date in YYYY-MM-DD format")
    max_infections: int = Field(..., ge=0)
    frames: list[InfectionTimelineFrame] = Field(default_factory=list)


class NeuralPredictionRequest(BaseModel):
    seed_country: str = Field(..., min_length=2, description="ISO-3 code or country name")
    start_date: str | None = Field(default=None, description="Optional forecast start date in YYYY-MM-DD format")


class NeuralPredictionFrame(BaseModel):
    day: int = Field(..., ge=1)
    date: str = Field(..., description="Forecast date in YYYY-MM-DD format")
    new_cases_by_country: dict[str, float] = Field(default_factory=dict)


class NeuralPredictionResponse(BaseModel):
    metric: str = Field(default="predicted_new_cases")
    seed_country_code: str = Field(..., description="Resolved seed ISO-3 code")
    seed_country_name: str = Field(..., description="Resolved seed country name")
    frame_count: int = Field(..., ge=1)
    start_date: str = Field(..., description="Forecast start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="Forecast end date in YYYY-MM-DD format")
    max_new_cases: float = Field(..., ge=0)
    frames: list[NeuralPredictionFrame] = Field(default_factory=list)
