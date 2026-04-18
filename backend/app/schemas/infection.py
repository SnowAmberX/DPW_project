from pydantic import BaseModel, Field


class InfectionSnapshotRequest(BaseModel):
    country_code: str = Field(..., min_length=3, max_length=3, description="ISO-3 country code from frontend click")


class InfectionSnapshotResponse(BaseModel):
    time: str = Field(..., description="Date string in YYYY:MM:DD format")
    infections_by_country: dict[str, int]
