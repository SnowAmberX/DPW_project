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
