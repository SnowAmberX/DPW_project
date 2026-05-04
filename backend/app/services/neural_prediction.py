"""Real TCN neural prediction service.

Replaces the deleted mock service. Loads the trained EpidemicTCN model and
preprocessing state, then runs inference given a seed (origin) country.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
WEIGHTS_DIR = PROJECT_ROOT / "backend" / "weights"
MODEL_PATH = WEIGHTS_DIR / "tcn_model.pt"
STATE_PATH = WEIGHTS_DIR / "preprocess_state.json"
CSV_PATH = PROJECT_ROOT / "data" / "raw_data" / "compact.csv"


def _resolve_seed_country(seed_country: str, country_list: list[str], country_codes: list[str]) -> tuple[int, str, str]:
    """Resolve seed_country to (index, name, iso3_code)."""
    seed = str(seed_country).strip()

    # Try exact match (name or code)
    for i, name in enumerate(country_list):
        if name.lower() == seed.lower() or country_codes[i].lower() == seed.lower():
            return i, name, country_codes[i]

    # Try partial match
    for i, name in enumerate(country_list):
        if seed.lower() in name.lower():
            return i, name, country_codes[i]

    raise ValueError(
        f"Country '{seed_country}' not found. Available: {', '.join(country_list[:20])}..."
    )


@lru_cache(maxsize=1)
def _load_preprocess_state() -> dict:
    if not STATE_PATH.exists():
        raise FileNotFoundError(
            f"Preprocess state not found at {STATE_PATH}. Run 'python model/train.py' first."
        )
    with open(STATE_PATH, "r") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_model() -> Any:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model checkpoint not found at {MODEL_PATH}. Run 'python model/train.py' first."
        )

    sys.path.insert(0, str(PROJECT_ROOT))
    import torch
    from model.model import EpidemicTCN

    checkpoint = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)

    model = EpidemicTCN(
        num_countries=checkpoint["num_countries"],
        num_dynamic_features=checkpoint["num_dynamic_features"],
        num_static_features=checkpoint["num_static_features"],
        history_days=checkpoint["history_days"],
        forecast_days=checkpoint["forecast_days"],
        hidden_size=checkpoint["hidden_size"],
        num_levels=checkpoint["num_levels"],
        dropout=checkpoint["dropout"],
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model


@lru_cache(maxsize=1)
def _load_recent_data() -> tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    """Load the most recent history window for all countries from compact.csv.

    Returns (dyn_array, static_array_norm, target_log, latest_date_str).
    """
    state = _load_preprocess_state()
    country_list = state["country_list"]
    dyn_features = state["dynamic_features"]
    static_features = state["static_features"]

    df = pd.read_csv(CSV_PATH, parse_dates=["date"])
    df = df[df["code"].notna() & df["code"].str.match(r"^[A-Z]{3}$")]
    df = df[df["country"].isin(country_list)]

    all_dates = sorted(df["date"].unique())
    history_days = state["history_days"]

    # Build dynamic array for all dates
    date_index = {d: i for i, d in enumerate(all_dates)}
    num_countries = len(country_list)
    num_dates = len(all_dates)

    dyn_array = np.full((num_countries, num_dates, len(dyn_features)), np.nan, dtype=np.float32)

    for ci, country in enumerate(country_list):
        cdf = df[df["country"] == country].sort_values("date")
        for _, row in cdf.iterrows():
            di = date_index[row["date"]]
            for fi, feat in enumerate(dyn_features):
                val = row.get(feat)
                if pd.notna(val) and np.isfinite(val):
                    dyn_array[ci, di, fi] = float(val)

    # Forward-fill and zero-fill
    for ci in range(num_countries):
        for fi in range(len(dyn_features)):
            col = dyn_array[ci, :, fi]
            mask = ~np.isnan(col)
            if mask.any():
                idx = np.where(mask)[0]
                values = col[mask]
                col[: idx[-1] + 1] = np.interp(np.arange(idx[-1] + 1), idx, values)
                col[idx[-1] + 1:] = values[-1]
            else:
                col[:] = 0.0
            col[np.isnan(col)] = 0.0

    # Load static features and normalize
    static_df = df.groupby("country")[static_features].first()
    static_df = static_df.fillna(static_df.median())
    static_array = static_df.reindex(country_list).values.astype(np.float32)

    static_mean = np.array(state["static_mean"], dtype=np.float32)
    static_std = np.array(state["static_std"], dtype=np.float32)
    static_array_norm = (static_array - static_mean) / static_std

    # Normalize dynamic features
    dyn_mean = np.array(state["dyn_mean"], dtype=np.float32)
    dyn_std = np.array(state["dyn_std"], dtype=np.float32)
    dyn_array_norm = (dyn_array - dyn_mean) / dyn_std

    # Extract the last history_days window
    last_date = all_dates[-1]
    last_idx = len(all_dates) - 1
    start_idx = max(0, last_idx - history_days)

    recent_dyn = dyn_array_norm[:, start_idx:last_idx, :]
    # Pad if needed
    if recent_dyn.shape[1] < history_days:
        pad = history_days - recent_dyn.shape[1]
        recent_dyn = np.pad(recent_dyn, ((0, 0), (pad, 0), (0, 0)), mode="edge")

    # Target log for denormalization
    target = np.log1p(np.maximum(dyn_array[:, :, 0], 0))

    return recent_dyn, static_array_norm, target, str(last_date.date())


def build_neural_prediction_timeline(
    seed_country: str,
    start_date: str | None = None,
) -> dict:
    """Run TCN inference and return structured prediction timeline.

    Args:
        seed_country: Country name or ISO-3 code of the outbreak origin.
        start_date: Optional forecast start date (ignored; uses latest data date).

    Returns:
        dict compatible with NeuralPredictionResponse schema.
    """
    try:
        state = _load_preprocess_state()
    except FileNotFoundError:
        raise

    try:
        model = _load_model()
    except FileNotFoundError:
        raise

    import torch

    country_list = state["country_list"]
    country_codes = state["country_codes"]
    forecast_days = state["forecast_days"]
    history_days = state["history_days"]

    # Resolve seed country
    seed_idx, seed_name, seed_code = _resolve_seed_country(seed_country, country_list, country_codes)

    # Load recent data
    recent_dyn, static_array_norm, target_log, latest_date_str = _load_recent_data()

    num_countries = len(country_list)

    country_ids = torch.arange(num_countries, dtype=torch.long)

    # Run inference
    with torch.no_grad():
        predictions_norm = model.predict(
            dynamic_features=torch.from_numpy(recent_dyn),
            static_features=torch.from_numpy(static_array_norm),
            origin_idx=seed_idx,
            country_ids=country_ids,
        )

    predictions_norm = predictions_norm.numpy()  # (N, forecast_days)

    # Denormalize predictions (per-country normalization)
    target_mean = np.array(state["target_mean"], dtype=np.float32)  # (N,)
    target_std = np.array(state["target_std"], dtype=np.float32)    # (N,)
    # Inverse of (x - mean) / std -> x * std + mean, then expm1
    predictions_log = predictions_norm * target_std[:, None] + target_mean[:, None]
    predictions_cases = np.expm1(predictions_log)
    predictions_cases = np.maximum(predictions_cases, 0)

    # Build dates
    base_date = (
        datetime.strptime(start_date, "%Y-%m-%d")
        if start_date
        else datetime.strptime(latest_date_str, "%Y-%m-%d")
    )

    frames = []
    max_cases = 0.0

    for day in range(1, forecast_days + 1):
        frame_date = base_date + timedelta(days=day)
        new_cases_by_country: dict[str, float] = {}

        for ci, country in enumerate(country_list):
            val = float(predictions_cases[ci, day - 1])
            if val > max_cases:
                max_cases = val
            new_cases_by_country[country] = val

        frames.append({
            "day": day,
            "date": frame_date.strftime("%Y-%m-%d"),
            "new_cases_by_country": new_cases_by_country,
        })

    return {
        "metric": "predicted_new_cases",
        "seed_country_code": seed_code,
        "seed_country_name": seed_name,
        "frame_count": len(frames),
        "start_date": frames[0]["date"],
        "end_date": frames[-1]["date"],
        "max_new_cases": max_cases,
        "frames": frames,
    }
