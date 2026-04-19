"""Single-pass global outbreak simulation from an arbitrary seed country."""

import argparse
from datetime import date
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import torch

from gnn_lstm import GNNRNNForecastModel


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CHECKPOINT = SCRIPT_DIR / "artifacts" / "checkpoint_gnn_rnn.pt"
DEFAULT_OUTPUT = SCRIPT_DIR / "output" / "outbreak_forecast.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate next-outbreak global spread from any seed country."
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        default=str(DEFAULT_CHECKPOINT),
        help="Model checkpoint path.",
    )
    parser.add_argument(
        "--seed-country",
        type=str,
        required=True,
        help="Outbreak origin country (ISO3 code or country name).",
    )
    parser.add_argument(
        "--seed-amplitude",
        type=float,
        default=12.0,
        help="A in log(1 + A * exp(r * t)) for seed outbreak curve.",
    )
    parser.add_argument(
        "--seed-growth-rate",
        type=float,
        default=0.22,
        help="r in log(1 + A * exp(r * t)) for seed outbreak curve.",
    )
    parser.add_argument(
        "--baseline-min",
        type=float,
        default=0.0,
        help="Lower bound of non-seed baseline cases before log1p.",
    )
    parser.add_argument(
        "--baseline-max",
        type=float,
        default=3.0,
        help="Upper bound of non-seed baseline cases before log1p.",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Optional forecast start date (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_OUTPUT),
        help="Output CSV path.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Random seed for baseline sampling.",
    )
    return parser.parse_args()


def _resolve_seed_country(
    seed_country: str,
    countries: List[str],
    name_to_code: Dict[str, str],
) -> str:
    key = seed_country.strip()
    if not key:
        raise ValueError("--seed-country cannot be empty.")

    key_upper = key.upper()
    if key_upper in countries:
        return key_upper

    key_lower = key.lower()
    if key_lower in name_to_code:
        code = str(name_to_code[key_lower]).upper()
        if code in countries:
            return code

    raise ValueError(
        f"Unknown seed country '{seed_country}'. Please use a valid ISO3 code or country name."
    )


def _build_smooth_baseline(
    num_nodes: int,
    seq_len: int,
    baseline_min: float,
    baseline_max: float,
    rng: np.random.Generator,
) -> np.ndarray:
    low = max(0.0, float(min(baseline_min, baseline_max)))
    high = max(low, float(max(baseline_min, baseline_max)))

    if high <= 0.0:
        return np.zeros((num_nodes, seq_len), dtype=np.float32)

    starts = rng.uniform(low, high, size=(num_nodes, 1)).astype(np.float32)
    ends = rng.uniform(low, high, size=(num_nodes, 1)).astype(np.float32)
    alpha = np.linspace(0.0, 1.0, seq_len, dtype=np.float32)[None, :]
    baseline_cases = starts * (1.0 - alpha) + ends * alpha
    return np.log1p(baseline_cases).astype(np.float32)


def _build_seed_curve(seq_len: int, amplitude: float, growth_rate: float) -> np.ndarray:
    amp = max(1e-6, float(amplitude))
    rate = float(growth_rate)
    t = np.arange(seq_len, dtype=np.float32)
    exp_term = np.exp(np.clip(rate * t, a_min=-20.0, a_max=20.0))
    curve = np.log1p(amp * exp_term)
    return curve.astype(np.float32)


def _resolve_start_date(start_date: str | None) -> pd.Timestamp:
    if not start_date:
        return pd.Timestamp(date.today())

    ts = pd.to_datetime(start_date, errors="coerce")
    if pd.isna(ts):
        raise ValueError(f"Invalid --start-date: {start_date}")
    return pd.Timestamp(ts)


def predict() -> None:
    args = parse_args()

    ckpt_path = Path(args.checkpoint).resolve()
    payload = torch.load(ckpt_path, map_location="cpu", weights_only=False)

    cfg = payload["config"]
    artifacts = payload["artifacts"]

    countries: List[str] = list(artifacts["countries"])
    name_to_code: Dict[str, str] = artifacts.get("name_to_code", {})
    code_to_name: Dict[str, str] = artifacts.get("code_to_name", {})

    seed_code = _resolve_seed_country(
        seed_country=args.seed_country,
        countries=countries,
        name_to_code=name_to_code,
    )
    seed_idx = int(countries.index(seed_code))

    static_features: torch.Tensor = artifacts["static_features"].float()
    edge_index: torch.Tensor = artifacts["edge_index"].long()
    edge_weight: torch.Tensor = artifacts["edge_weight"].float()

    seq_len = int(cfg["seq_len"])
    horizon = int(cfg["horizon"])
    num_nodes = len(countries)

    input_dim = int(cfg["input_dim"])
    static_dim = int(static_features.shape[1])
    dynamic_dim = input_dim - static_dim
    if dynamic_dim not in (1, 2):
        raise ValueError(
            f"Unsupported dynamic_dim={dynamic_dim}. Expected 1 (log_cases) or 2 (log_cases + seed_flag)."
        )

    model = GNNRNNForecastModel(
        num_nodes=int(cfg["num_nodes"]),
        input_dim=input_dim,
        hidden_dim=int(cfg["hidden_dim"]),
        horizon=horizon,
        rnn_type=str(cfg["rnn_type"]),
        rnn_layers=int(cfg["rnn_layers"]),
        gat_heads=int(cfg.get("gat_heads", 4)),
    )
    model.load_state_dict(payload["model_state_dict"])
    model.eval()

    rng = np.random.default_rng(seed=int(args.random_seed))

    # Start from low non-zero baseline for all countries to avoid synthetic train/infer mismatch.
    log_hist = _build_smooth_baseline(
        num_nodes=num_nodes,
        seq_len=seq_len,
        baseline_min=args.baseline_min,
        baseline_max=args.baseline_max,
        rng=rng,
    )

    # Inject a smooth seed outbreak curve at the selected origin country.
    seed_curve = _build_seed_curve(
        seq_len=seq_len,
        amplitude=args.seed_amplitude,
        growth_rate=args.seed_growth_rate,
    )
    log_hist[seed_idx] = seed_curve

    x = torch.zeros((1, num_nodes, seq_len, input_dim), dtype=torch.float32)
    x[0, :, :, 0] = torch.from_numpy(log_hist)
    x[0, :, :, 1 : 1 + static_dim] = static_features[:, None, :]

    if dynamic_dim == 2:
        seed_flag = torch.zeros((num_nodes,), dtype=torch.float32)
        seed_flag[seed_idx] = 1.0
        x[0, :, :, -1] = seed_flag[:, None]

    with torch.no_grad():
        pred_log = model(x, edge_index, edge_weight)[0].cpu().numpy()  # (N, horizon)

    pred_log = np.clip(pred_log, a_min=-20.0, a_max=20.0)
    pred_cases = np.expm1(pred_log)
    pred_cases = np.clip(pred_cases, a_min=0.0, a_max=None)

    forecast_start = _resolve_start_date(args.start_date)

    rows = []
    for i, code in enumerate(countries):
        country_name = code_to_name.get(code, code)
        for t in range(horizon):
            rows.append(
                {
                    "day": t + 1,
                    "forecast_date": (forecast_start + pd.Timedelta(days=t)).date().isoformat(),
                    "country_code": code,
                    "country_name": country_name,
                    "seed_country_code": seed_code,
                    "predicted_new_cases": float(pred_cases[i, t]),
                }
            )

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_path, index=False)

    print(f"Seed country: {seed_code} ({code_to_name.get(seed_code, seed_code)})")
    print(
        f"Seed curve params: amplitude={float(args.seed_amplitude):.4g}, growth_rate={float(args.seed_growth_rate):.4g}"
    )
    print(
        f"Baseline cases range: [{max(0.0, min(args.baseline_min, args.baseline_max)):.3f}, "
        f"{max(max(0.0, min(args.baseline_min, args.baseline_max)), max(args.baseline_min, args.baseline_max)):.3f}]"
    )
    print(f"Forecast horizon: {horizon} day(s)")
    print(f"Output tensor shape (N, horizon): ({num_nodes}, {horizon})")
    print(f"Saved forecast CSV: {output_path}")


if __name__ == "__main__":
    predict()
