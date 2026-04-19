"""Single-pass global outbreak forecasting from real historical observations."""

import argparse
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import torch

from gnn_lstm import GNNRNNForecastModel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Forecast global daily infections from real historical windows."
    )
    parser.add_argument(
        "--checkpoint", type=str, default="./artifacts/checkpoint_gnn_rnn.pt"
    )
    parser.add_argument("--data", type=str, default="../../data/raw_data/compact.csv")
    parser.add_argument(
        "--window-end-date",
        type=str,
        default=None,
        help="Optional end date (YYYY-MM-DD) for historical input window.",
    )
    parser.add_argument("--output", type=str, default="./output/outbreak_forecast.csv")
    return parser.parse_args()


def _load_history_window(
    data_csv_path: Path,
    countries: List[str],
    seq_len: int,
    window_end_date: Optional[str],
) -> Tuple[np.ndarray, pd.Timestamp]:
    usecols = ["date", "code", "new_cases_smoothed"]
    df = pd.read_csv(data_csv_path, usecols=usecols)

    df = df[df["code"].astype(str).str.fullmatch(r"[A-Z]{3}", na=False)].copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["new_cases_smoothed"] = pd.to_numeric(df["new_cases_smoothed"], errors="coerce")
    df = df.dropna(subset=["date", "new_cases_smoothed"])

    if window_end_date:
        end_ts = pd.to_datetime(window_end_date, errors="coerce")
        if pd.isna(end_ts):
            raise ValueError(f"Invalid --window-end-date: {window_end_date}")
        df = df[df["date"] <= end_ts]

    ts = df.pivot_table(
        index="date",
        columns="code",
        values="new_cases_smoothed",
        aggfunc="mean",
    ).sort_index()

    ts = ts.reindex(columns=countries)
    ts = ts.fillna(0.0)

    if len(ts) < seq_len:
        raise ValueError(
            f"Not enough history for seq_len={seq_len}: only {len(ts)} day(s) available."
        )

    hist = ts.tail(seq_len)
    hist_values = hist.to_numpy(dtype=np.float32)
    hist_values = np.clip(hist_values, a_min=0.0, a_max=None)
    log_hist = np.log1p(hist_values).astype(np.float32)
    return log_hist, pd.Timestamp(hist.index.max())


def predict() -> None:
    args = parse_args()
    ckpt_path = Path(args.checkpoint).resolve()
    data_path = Path(args.data).resolve()

    payload = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    cfg = payload["config"]
    artifacts = payload["artifacts"]

    model = GNNRNNForecastModel(
        num_nodes=int(cfg["num_nodes"]),
        input_dim=int(cfg["input_dim"]),
        hidden_dim=int(cfg["hidden_dim"]),
        horizon=int(cfg["horizon"]),
        rnn_type=str(cfg["rnn_type"]),
        rnn_layers=int(cfg["rnn_layers"]),
        gat_heads=int(cfg.get("gat_heads", 4)),
    )
    model.load_state_dict(payload["model_state_dict"])
    model.eval()

    countries = artifacts["countries"]
    code_to_name = artifacts.get("code_to_name", {})

    static_features: torch.Tensor = artifacts["static_features"].float()
    edge_index: torch.Tensor = artifacts["edge_index"].long()
    edge_weight: torch.Tensor = artifacts["edge_weight"].float()

    seq_len = int(cfg["seq_len"])
    horizon = int(cfg["horizon"])
    num_nodes = len(countries)

    input_dim = int(cfg["input_dim"])
    static_dim = int(static_features.shape[1])
    dynamic_dim = input_dim - static_dim
    if dynamic_dim != 1:
        raise ValueError(
            f"Expected dynamic_dim=1 (log_cases only), got {dynamic_dim}."
        )

    log_hist, history_end = _load_history_window(
        data_csv_path=data_path,
        countries=countries,
        seq_len=seq_len,
        window_end_date=args.window_end_date,
    )

    x = torch.zeros((1, num_nodes, seq_len, input_dim), dtype=torch.float32)
    x[0, :, :, 0] = torch.from_numpy(log_hist.T)
    x[0, :, :, 1:] = static_features[:, None, :]

    with torch.no_grad():
        pred_log = model(x, edge_index, edge_weight)[0].cpu().numpy()  # (N, horizon)

    pred_cases = np.expm1(pred_log)
    pred_cases = np.clip(pred_cases, a_min=0.0, a_max=None)

    rows = []
    for i, code in enumerate(countries):
        country_name = code_to_name.get(code, code)
        for t in range(horizon):
            forecast_date = (history_end + pd.Timedelta(days=t + 1)).date().isoformat()
            rows.append(
                {
                    "day": t + 1,
                    "forecast_date": forecast_date,
                    "country_code": code,
                    "country_name": country_name,
                    "predicted_new_cases": float(pred_cases[i, t]),
                }
            )

    df = pd.DataFrame(rows)
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"History window end date: {history_end.date().isoformat()}")
    print(f"Forecast horizon: {horizon} day(s)")
    print(f"Output tensor shape (T, N, 1): ({horizon}, {num_nodes}, 1)")
    print(f"Saved forecast CSV: {output_path}")


if __name__ == "__main__":
    predict()
