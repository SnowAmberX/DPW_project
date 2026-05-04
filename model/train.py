"""Train the EpidemicTCN model on OWID compact.csv data.

Usage: python model/train.py
Output: backend/weights/tcn_model.pt, backend/weights/preprocess_state.pt
"""

import json
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader, TensorDataset

warnings.filterwarnings("ignore", category=FutureWarning)

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from model.model import EpidemicTCN

# ── Config ──────────────────────────────────────────────────────────────
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
CSV_PATH = Path("data/raw_data/compact.csv")
WEIGHTS_DIR = Path("backend/weights")

HISTORY_DAYS = 14
FORECAST_DAYS = 80
BATCH_SIZE = 32
EPOCHS = 200
LEARNING_RATE = 1e-3
HIDDEN_SIZE = 128
TCN_LEVELS = 5
DROPOUT = 0.1
TRAIN_SPLIT_DATE = "2023-01-01"
MIN_POPULATION = 1_000_000
SAMPLE_STRIDE = 2  # more samples

DYNAMIC_FEATURES = [
    "new_cases_smoothed",
    "total_cases",
    "new_deaths_smoothed",
    "stringency_index",
    "people_vaccinated_per_hundred",
    "reproduction_rate",
]

STATIC_FEATURES = [
    "population_density",
    "gdp_per_capita",
    "median_age",
    "life_expectancy",
    "diabetes_prevalence",
    "hospital_beds_per_thousand",
]


# ── Data Loading ────────────────────────────────────────────────────────
def load_and_preprocess():
    df = pd.read_csv(CSV_PATH, parse_dates=["date"])

    # Keep only valid ISO-3 countries with sufficient population
    df = df[df["code"].notna() & df["code"].str.match(r"^[A-Z]{3}$")].copy()
    df = df[df["population"] >= MIN_POPULATION]

    country_list = sorted(df["country"].unique())
    country_codes = df.groupby("country")["code"].first().reindex(country_list).tolist()

    # Gather static features per country
    static_df = df.groupby("country")[STATIC_FEATURES].first()
    # Some static features may still be NaN; fill with median
    static_df = static_df.fillna(static_df.median())

    # Build 3D array: (num_countries, num_dates, num_dynamic_features)
    num_countries = len(country_list)
    all_dates = sorted(df["date"].unique())
    date_index = {d: i for i, d in enumerate(all_dates)}
    num_dates = len(all_dates)

    dyn_array = np.full((num_countries, num_dates, len(DYNAMIC_FEATURES)), np.nan, dtype=np.float32)

    for ci, country in enumerate(country_list):
        cdf = df[df["country"] == country].sort_values("date")
        for _, row in cdf.iterrows():
            di = date_index[row["date"]]
            for fi, feat in enumerate(DYNAMIC_FEATURES):
                val = row.get(feat)
                if pd.notna(val) and np.isfinite(val):
                    dyn_array[ci, di, fi] = float(val)

    # Forward-fill along time axis, then fill remaining with 0
    for ci in range(num_countries):
        for fi in range(len(DYNAMIC_FEATURES)):
            col = dyn_array[ci, :, fi]
            mask = ~np.isnan(col)
            if mask.any():
                idx = np.where(mask)[0]
                values = col[mask]
                col[: idx[-1] + 1] = np.interp(
                    np.arange(idx[-1] + 1), idx, values
                )
                col[idx[-1] + 1:] = values[-1]
            else:
                col[:] = 0.0
            col[np.isnan(col)] = 0.0

    # Static features as float32
    static_array = static_df.reindex(country_list).values.astype(np.float32)

    # Compute normalization stats (on training portion only)
    train_date_limit = pd.Timestamp(TRAIN_SPLIT_DATE)
    train_mask = np.array([pd.Timestamp(d) < train_date_limit for d in all_dates])

    dyn_mean = np.nanmean(dyn_array[:, train_mask, :], axis=(0, 1), keepdims=True)
    dyn_std = np.nanstd(dyn_array[:, train_mask, :], axis=(0, 1), keepdims=True)
    dyn_std[dyn_std < 1e-8] = 1.0

    dyn_array_norm = (dyn_array - dyn_mean) / dyn_std

    static_mean = np.mean(static_array, axis=0, keepdims=True)
    static_std = np.std(static_array, axis=0, keepdims=True)
    static_std[static_std < 1e-8] = 1.0
    static_array_norm = (static_array - static_mean) / static_std

    # Target: log1p of new_cases_smoothed (index 0)
    target = np.log1p(np.maximum(dyn_array[:, :, 0], 0))

    # Per-country normalization (forces model to learn country-specific patterns)
    target_mean = np.mean(target[:, train_mask], axis=1, keepdims=True)  # (N, 1)
    target_std = np.std(target[:, train_mask], axis=1, keepdims=True) + 1e-8  # (N, 1)
    target_norm = (target - target_mean) / target_std

    # Global stats for reference only
    global_target_mean = float(np.mean(target[:, train_mask]))
    global_target_std = float(np.std(target[:, train_mask]))

    # Save preprocessing state for inference
    preprocess_state = {
        "country_list": country_list,
        "country_codes": country_codes,
        "static_array": static_array.tolist(),
        "all_dates": [str(d.date()) for d in all_dates],
        "dyn_mean": dyn_mean.squeeze(0).tolist(),
        "dyn_std": dyn_std.squeeze(0).tolist(),
        "static_mean": static_mean.squeeze(0).tolist(),
        "static_std": static_std.squeeze(0).tolist(),
        "target_mean": target_mean.squeeze(1).tolist(),
        "target_std": target_std.squeeze(1).tolist(),
        "dynamic_features": DYNAMIC_FEATURES,
        "static_features": STATIC_FEATURES,
        "history_days": HISTORY_DAYS,
        "forecast_days": FORECAST_DAYS,
    }
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(WEIGHTS_DIR / "preprocess_state.json", "w") as f:
        json.dump(preprocess_state, f, indent=2)

    return (
        dyn_array_norm, static_array_norm, target_norm,
        country_list, all_dates, train_mask, num_countries,
    )


# ── Sample Builder ──────────────────────────────────────────────────────
def build_samples(dyn_array, static_array, target, train_mask, num_countries):
    """Create (history_window -> future_target) sliding-window samples.

    For each valid time step, randomly designate one country as the origin.
    Uses SAMPLE_STRIDE to reduce memory footprint.
    """
    num_dates = dyn_array.shape[1]
    max_start = num_dates - HISTORY_DAYS - FORECAST_DAYS
    all_train_indices = np.where(train_mask[:max_start])[0]
    train_indices = all_train_indices[::SAMPLE_STRIDE]
    np.random.seed(42)

    num_samples = len(train_indices)
    print(f"  Creating {num_samples} samples (stride={SAMPLE_STRIDE})...")

    X_dyn = np.zeros((num_samples, num_countries, HISTORY_DAYS, len(DYNAMIC_FEATURES)), dtype=np.float32)
    Y = np.zeros((num_samples, num_countries, FORECAST_DAYS), dtype=np.float32)
    X_origin = np.zeros(num_samples, dtype=np.int32)

    for si, t in enumerate(train_indices):
        if (si + 1) % 50 == 0:
            print(f"    ... {si + 1}/{num_samples}")

        X_dyn[si] = dyn_array[:, t:t + HISTORY_DAYS, :]
        Y[si] = target[:, t + HISTORY_DAYS:t + HISTORY_DAYS + FORECAST_DAYS]
        X_origin[si] = np.random.randint(0, num_countries)

    # Static features are the same for all samples
    X_static = np.tile(static_array[np.newaxis, :, :], (num_samples, 1, 1))

    return X_dyn, X_static, X_origin, Y


def build_origin_masks(origin_indices, num_countries, batch_size):
    """Convert origin country indices to binary masks."""
    masks = np.zeros((batch_size, num_countries, 1), dtype=np.float32)
    for i, idx in enumerate(origin_indices):
        masks[i, idx, 0] = 1.0
    return masks


# ── Training ────────────────────────────────────────────────────────────
def train():
    print(f"Device: {DEVICE}")
    print("Loading data...")
    dyn_array, static_array, target, country_list, all_dates, train_mask, num_countries = (
        load_and_preprocess()
    )
    print(f"Countries: {num_countries}, Dates: {len(all_dates)}")

    print("Building samples...")
    X_dyn, X_static, X_origin, Y = build_samples(
        dyn_array, static_array, target, train_mask, num_countries
    )
    print(f"Train samples: {X_dyn.shape[0]}")
    print(f"X_dyn: {X_dyn.shape}, Y: {Y.shape}")

    # Split train/val
    n_total = X_dyn.shape[0]
    n_val = int(n_total * 0.1)
    indices = np.random.RandomState(42).permutation(n_total)
    val_idx, train_idx = indices[:n_val], indices[n_val:]

    # Country IDs for embedding
    country_ids = torch.arange(num_countries, dtype=torch.long)

    # Create DataLoaders
    train_dataset = TensorDataset(
        torch.from_numpy(X_dyn[train_idx]),
        torch.from_numpy(X_static[train_idx]),
        torch.from_numpy(X_origin[train_idx]).long(),
        torch.from_numpy(Y[train_idx]),
    )
    val_dataset = TensorDataset(
        torch.from_numpy(X_dyn[val_idx]),
        torch.from_numpy(X_static[val_idx]),
        torch.from_numpy(X_origin[val_idx]).long(),
        torch.from_numpy(Y[val_idx]),
    )

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, drop_last=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, drop_last=False)

    print("Building model...")
    model = EpidemicTCN(
        num_countries=num_countries,
        num_dynamic_features=len(DYNAMIC_FEATURES),
        num_static_features=len(STATIC_FEATURES),
        history_days=HISTORY_DAYS,
        forecast_days=FORECAST_DAYS,
        hidden_size=HIDDEN_SIZE,
        num_levels=TCN_LEVELS,
        dropout=DROPOUT,
    ).to(DEVICE)

    print(f"Parameters: {sum(p.numel() for p in model.parameters()):,}")

    optimizer = AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-4)
    scheduler = CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-5)
    criterion = nn.HuberLoss(delta=1.0)

    country_ids = country_ids.to(DEVICE)

    best_val_loss = float("inf")
    patience = 30
    patience_counter = 0

    for epoch in range(1, EPOCHS + 1):
        model.train()
        train_loss = 0.0
        for batch_dyn, batch_static, batch_origin, batch_y in train_loader:
            batch_dyn = batch_dyn.to(DEVICE)
            batch_static = batch_static.to(DEVICE)
            batch_y = batch_y.to(DEVICE)
            bs = batch_dyn.size(0)

            origin_mask = build_origin_masks(batch_origin.numpy(), num_countries, bs)
            origin_mask = torch.from_numpy(origin_mask).to(DEVICE)
            cid_batch = country_ids.unsqueeze(0).expand(bs, -1).to(DEVICE)

            optimizer.zero_grad()
            pred = model(batch_dyn, batch_static, origin_mask, cid_batch)
            loss = criterion(pred, batch_y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss += loss.item()

        train_loss /= len(train_loader)

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for batch_dyn, batch_static, batch_origin, batch_y in val_loader:
                batch_dyn = batch_dyn.to(DEVICE)
                batch_static = batch_static.to(DEVICE)
                batch_y = batch_y.to(DEVICE)
                bs = batch_dyn.size(0)

                origin_mask = build_origin_masks(batch_origin.numpy(), num_countries, bs)
                origin_mask = torch.from_numpy(origin_mask).to(DEVICE)
                cid_batch = country_ids.unsqueeze(0).expand(bs, -1).to(DEVICE)

                pred = model(batch_dyn, batch_static, origin_mask, cid_batch)
                loss = criterion(pred, batch_y)
                val_loss += loss.item()

        val_loss /= len(val_loader)
        scheduler.step()

        if epoch % 5 == 0 or epoch == 1:
            print(f"Epoch {epoch:3d}/{EPOCHS} | train_loss={train_loss:.4f} | val_loss={val_loss:.4f} | lr={scheduler.get_last_lr()[0]:.2e}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "num_countries": num_countries,
                    "num_dynamic_features": len(DYNAMIC_FEATURES),
                    "num_static_features": len(STATIC_FEATURES),
                    "history_days": HISTORY_DAYS,
                    "forecast_days": FORECAST_DAYS,
                    "hidden_size": HIDDEN_SIZE,
                    "num_levels": TCN_LEVELS,
                    "dropout": DROPOUT,
                    "dynamic_features": DYNAMIC_FEATURES,
                    "static_features": STATIC_FEATURES,
                },
                WEIGHTS_DIR / "tcn_model.pt",
            )
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"Early stopping at epoch {epoch}")
                break

    print(f"Training complete. Best val loss: {best_val_loss:.4f}")
    print(f"Model saved to {WEIGHTS_DIR / 'tcn_model.pt'}")


if __name__ == "__main__":
    train()
