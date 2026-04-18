import logging

from fastapi import APIRouter

from app.schemas.infection import InfectionSnapshotRequest, InfectionSnapshotResponse
from app.services.mock_data import generate_mock_snapshot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/infections", tags=["infections"])


@router.post("/snapshot", response_model=InfectionSnapshotResponse)
def get_infection_snapshot(payload: InfectionSnapshotRequest) -> InfectionSnapshotResponse:
    country_code = payload.country_code.upper()

    # 测试联通性时，在后端打印前端传来的国家代码
    print(f"[backend] country_code received: {country_code}")
    logger.info("country_code received: %s", country_code)

    snapshot = generate_mock_snapshot()
    return InfectionSnapshotResponse(**snapshot)
