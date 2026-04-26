from __future__ import annotations

import importlib
import sys
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
NEURAL_DIR = PROJECT_ROOT / "model" / "neural"
ARTIFACTS_DIR = NEURAL_DIR / "artifacts"
CHECKPOINT_CANDIDATES = (
    ARTIFACTS_DIR / "checkpoint_gnn_rnn.pt",
)


def _resolve_checkpoint_path() -> Path:
    for candidate in CHECKPOINT_CANDIDATES:
        if candidate.exists():
            return candidate

    searched = ", ".join(str(path) for path in CHECKPOINT_CANDIDATES)
    raise FileNotFoundError(f"No neural checkpoint found. Checked: {searched}")


def _load_neural_dependencies() -> tuple[Any, Any, Any, Any]:
    try:
        import numpy as np
        import pandas as pd
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "Neural prediction dependencies are missing. Install with: "
            "uv pip install -r model/neural/requirements.txt"
        ) from exc

    if str(NEURAL_DIR) not in sys.path:
        sys.path.insert(0, str(NEURAL_DIR))

    try:
        gnn_module = importlib.import_module("gnn_lstm")
        model_cls = getattr(gnn_module, "GNNRNNForecastModel")
    except Exception as exc:  # noqa: BLE001 - provide a clearer runtime message for API consumers.
        raise RuntimeError(
            "Failed to import neural model class. Ensure torch-geometric is installed "
            "for the current Python environment."
        ) from exc
 
    return np, pd, torch, model_cls


def _resolve_seed_country(seed_country: str, countries: list[str], name_to_code: dict[str, str]) -> str:
    key = seed_country.strip()
    if not key:
        raise ValueError("seed_country cannot be empty.")

    key_upper = key.upper()
    if key_upper in countries:
        return key_upper

    key_lower = key.lower()
    if key_lower in name_to_code:
        code = str(name_to_code[key_lower]).upper()
        if code in countries:
            return code

    raise ValueError(f"Unknown seed_country '{seed_country}'. Please use a valid ISO-3 code or country name.")


def _build_smooth_baseline(
    np_module: Any,
    num_nodes: int,
    seq_len: int,
    baseline_min: float,
    baseline_max: float,
    random_seed: int,
) -> Any:
    low = max(0.0, float(min(baseline_min, baseline_max)))
    high = max(low, float(max(baseline_min, baseline_max)))

    if high <= 0.0:
        return np_module.zeros((num_nodes, seq_len), dtype=np_module.float32)

    rng = np_module.random.default_rng(seed=random_seed)
    starts = rng.uniform(low, high, size=(num_nodes, 1)).astype(np_module.float32)
    ends = rng.uniform(low, high, size=(num_nodes, 1)).astype(np_module.float32)
    alpha = np_module.linspace(0.0, 1.0, seq_len, dtype=np_module.float32)[None, :]
    baseline_cases = starts * (1.0 - alpha) + ends * alpha
    return np_module.log1p(baseline_cases).astype(np_module.float32)


def _build_seed_curve(np_module: Any, seq_len: int, amplitude: float, growth_rate: float) -> Any:
    amp = max(1e-6, float(amplitude))
    rate = float(growth_rate)
    t = np_module.arange(seq_len, dtype=np_module.float32)
    exp_term = np_module.exp(np_module.clip(rate * t, a_min=-20.0, a_max=20.0))
    curve = np_module.log1p(amp * exp_term)
    return curve.astype(np_module.float32)


def _resolve_start_date(start_date: str | None, pd_module: Any) -> Any:
    if not start_date:
        return pd_module.Timestamp(date.today())

    timestamp = pd_module.to_datetime(start_date, errors="coerce")
    if pd_module.isna(timestamp):
        raise ValueError(f"Invalid start_date: {start_date}. Expected YYYY-MM-DD.")
    return pd_module.Timestamp(timestamp)


@lru_cache(maxsize=1)
def _load_predictor() -> dict[str, Any]:
    np_module, pd_module, torch_module, model_cls = _load_neural_dependencies()
    checkpoint_path = _resolve_checkpoint_path()

    payload = torch_module.load(checkpoint_path, map_location="cpu", weights_only=False)
    cfg = payload["config"]
    artifacts = payload["artifacts"]

    countries = list(artifacts["countries"])
    name_to_code = dict(artifacts.get("name_to_code", {}))
    code_to_name = dict(artifacts.get("code_to_name", {}))

    static_features = artifacts["static_features"].float()
    edge_index = artifacts["edge_index"].long()
    edge_weight = artifacts["edge_weight"].float()

    input_dim = int(cfg["input_dim"])
    static_dim = int(static_features.shape[1])
    dynamic_dim = input_dim - static_dim
    if dynamic_dim not in (1, 2):
        raise ValueError(
            f"Unsupported dynamic_dim={dynamic_dim}. Expected 1 (log_cases) or 2 (log_cases + seed_flag)."
        )

    model = model_cls(
        num_nodes=int(cfg["num_nodes"]),
        input_dim=input_dim,
        hidden_dim=int(cfg["hidden_dim"]),
        horizon=int(cfg["horizon"]),
        rnn_type=str(cfg["rnn_type"]),
        rnn_layers=int(cfg["rnn_layers"]),
        gat_heads=int(cfg.get("gat_heads", 4)),
    )
    model.load_state_dict(payload["model_state_dict"])
    model.eval()

    return {
        "np": np_module,
        "pd": pd_module,
        "torch": torch_module,
        "model": model,
        "countries": countries,
        "name_to_code": name_to_code,
        "code_to_name": code_to_name,
        "static_features": static_features,
        "edge_index": edge_index,
        "edge_weight": edge_weight,
        "seq_len": int(cfg["seq_len"]),
        "horizon": int(cfg["horizon"]),
        "input_dim": input_dim,
        "static_dim": static_dim,
        "dynamic_dim": dynamic_dim,
    }


def build_neural_prediction_timeline(seed_country: str, start_date: str | None = None) -> dict[str, Any]:
    predictor = _load_predictor()
    np_module = predictor["np"]
    pd_module = predictor["pd"]
    torch_module = predictor["torch"]

    countries: list[str] = predictor["countries"]
    name_to_code: dict[str, str] = predictor["name_to_code"]
    code_to_name: dict[str, str] = predictor["code_to_name"]

    seed_code = _resolve_seed_country(seed_country=seed_country, countries=countries, name_to_code=name_to_code)
    seed_idx = int(countries.index(seed_code))

    seq_len = int(predictor["seq_len"])
    horizon = int(predictor["horizon"])
    num_nodes = len(countries)

    static_features = predictor["static_features"]
    edge_index = predictor["edge_index"]
    edge_weight = predictor["edge_weight"]
    input_dim = int(predictor["input_dim"])
    static_dim = int(predictor["static_dim"])
    dynamic_dim = int(predictor["dynamic_dim"])

    log_history = _build_smooth_baseline(
        np_module=np_module,
        num_nodes=num_nodes,
        seq_len=seq_len,
        baseline_min=0.0,
        baseline_max=3.0,
        random_seed=42,
    )
    log_history[seed_idx] = _build_seed_curve(
        np_module=np_module,
        seq_len=seq_len,
        amplitude=12.0,
        growth_rate=0.22,
    )

    x = torch_module.zeros((1, num_nodes, seq_len, input_dim), dtype=torch_module.float32)
    x[0, :, :, 0] = torch_module.from_numpy(log_history)
    x[0, :, :, 1 : 1 + static_dim] = static_features[:, None, :]

    if dynamic_dim == 2:
        seed_flag = torch_module.zeros((num_nodes,), dtype=torch_module.float32)
        seed_flag[seed_idx] = 1.0
        x[0, :, :, -1] = seed_flag[:, None]

    model = predictor["model"]
    with torch_module.no_grad():
        predicted_log = model(x, edge_index, edge_weight)[0].cpu().numpy()

    predicted_log = np_module.clip(predicted_log, a_min=-20.0, a_max=20.0)
    predicted_cases = np_module.expm1(predicted_log)
    predicted_cases = np_module.clip(predicted_cases, a_min=0.0, a_max=None)

    forecast_start = _resolve_start_date(start_date=start_date, pd_module=pd_module)
    max_new_cases = float(np_module.max(predicted_cases)) if predicted_cases.size else 0.0

    frames: list[dict[str, Any]] = []
    for day_index in range(horizon):
        frame_date = (forecast_start + pd_module.Timedelta(days=day_index)).date().isoformat()
        values: dict[str, float] = {}

        for country_index, code in enumerate(countries):
            country_name = code_to_name.get(code, code)
            values[country_name] = float(predicted_cases[country_index, day_index])

        frames.append(
            {
                "day": day_index + 1,
                "date": frame_date,
                "new_cases_by_country": values,
            }
        )

    if not frames:
        raise ValueError("Model returned no forecast frames.")

    return {
        "metric": "predicted_new_cases",
        "seed_country_code": seed_code,
        "seed_country_name": code_to_name.get(seed_code, seed_code),
        "frame_count": len(frames),
        "start_date": frames[0]["date"],
        "end_date": frames[-1]["date"],
        "max_new_cases": max_new_cases,
        "frames": frames,
    }