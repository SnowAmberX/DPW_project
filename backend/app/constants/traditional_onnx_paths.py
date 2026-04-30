from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _resolve_traditional_onnx_artifacts_dir() -> Path:
    candidates = [
        PROJECT_ROOT / "model" / "ML_modelONNX" / "artifacts_country_v4_simple",
        PROJECT_ROOT / "model" / "ML_model" / "artifacts_country_v4_simple",
        PROJECT_ROOT / "model" / "model" / "artifacts_country_v4_simple",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]


TRADITIONAL_ONNX_ARTIFACTS_DIR = _resolve_traditional_onnx_artifacts_dir()
TRADITIONAL_ONNX_MODEL_REGISTRY_PATH = TRADITIONAL_ONNX_ARTIFACTS_DIR / "model_registry.json"
TRADITIONAL_ONNX_PANEL_DATA_PATH = PROJECT_ROOT / "data" / "processed_data" / "cleaned_panel_country_day.csv"
TRADITIONAL_ONNX_CASES_DATA_PATH = PROJECT_ROOT / "data" / "processed_data" / "cleaned_cases_deaths.csv"
