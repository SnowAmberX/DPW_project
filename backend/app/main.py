import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.health import router as health_router
from app.routers.infection import router as infection_router

logger = logging.getLogger(__name__)


def _warm_models() -> None:
    """Pre‑load both models into memory so the first request is fast."""
    from app.services.neural_prediction import warm_neural_cache
    from app.services.traditional_onnx.traditional_onnx_forecast_service import (
        warm_traditional_onnx_cache,
    )

    try:
        warm_neural_cache()
        logger.info("Neural TCN model cache warmed successfully.")
    except FileNotFoundError as exc:
        logger.warning("Neural TCN model cache warm skipped (artifacts not found): %s", exc)
    except Exception:
        logger.exception("Neural TCN model cache warm failed unexpectedly.")

    try:
        warm_traditional_onnx_cache()
        logger.info("Traditional ONNX model cache warmed successfully.")
    except FileNotFoundError as exc:
        logger.warning("Traditional ONNX model cache warm skipped (artifacts not found): %s", exc)
    except Exception:
        logger.exception("Traditional ONNX model cache warm failed unexpectedly.")


@asynccontextmanager
async def lifespan(application: FastAPI):
    _warm_models()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="COVID Map Backend",
    description="Testing backend for frontend map connectivity",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(infection_router)
