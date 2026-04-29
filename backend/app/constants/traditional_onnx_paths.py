from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TRADITIONAL_ONNX_ARTIFACTS_DIR = PROJECT_ROOT / "model" / "model" / "artifacts_country_v4_simple"
TRADITIONAL_ONNX_MODEL_REGISTRY_PATH = TRADITIONAL_ONNX_ARTIFACTS_DIR / "model_registry.json"
TRADITIONAL_ONNX_PANEL_DATA_PATH = PROJECT_ROOT / "data" / "processed_data" / "cleaned_panel_country_day.csv"
TRADITIONAL_ONNX_CASES_DATA_PATH = PROJECT_ROOT / "data" / "processed_data" / "cleaned_cases_deaths.csv"
