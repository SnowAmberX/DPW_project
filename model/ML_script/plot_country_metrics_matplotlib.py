from __future__ import annotations

from pathlib import Path
import json

import matplotlib.pyplot as plt
import pandas as pd


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    metrics_path = root / "ML_model" / "artifacts_country_v4_simple" / "country_metrics.json"
    output_dir = root / "ML_model" / "artifacts_country_v4_simple" / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)

    with metrics_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    numeric_cols = ["train_r2", "test_r2", "test_rmse", "test_smape", "test_rows", "best_iteration"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["gap_r2"] = df["train_r2"] - df["test_r2"]

    # Figure 1: test_r2 distribution
    plt.figure(figsize=(10, 5))
    plt.hist(df["test_r2"].dropna(), bins=60, color="#1f77b4", edgecolor="white")
    plt.title("Distribution of test_r2")
    plt.xlabel("test_r2")
    plt.ylabel("Country count")
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(output_dir / "01_test_r2_distribution.png", dpi=150)
    plt.close()

    # Figure 2: test_smape distribution
    plt.figure(figsize=(10, 5))
    plt.hist(df["test_smape"].dropna(), bins=60, color="#ff7f0e", edgecolor="white")
    plt.title("Distribution of test_smape")
    plt.xlabel("test_smape")
    plt.ylabel("Country count")
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(output_dir / "02_test_smape_distribution.png", dpi=150)
    plt.close()

    # Figure 3: train_r2 vs test_r2
    plt.figure(figsize=(8, 8))
    x = df["train_r2"].clip(-2, 1.2)
    y = df["test_r2"].clip(-2, 1.2)
    plt.scatter(x, y, s=18, alpha=0.65, color="#2ca02c")
    plt.plot([-2, 1.2], [-2, 1.2], "--", color="gray", linewidth=1)
    plt.title("Generalization check: train_r2 vs test_r2 (clipped)")
    plt.xlabel("train_r2")
    plt.ylabel("test_r2")
    plt.xlim(-2, 1.2)
    plt.ylim(-2, 1.2)
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(output_dir / "03_train_vs_test_r2_scatter.png", dpi=150)
    plt.close()

    # Figure 4: Top/Bottom 15 countries by test_r2
    top_n = 15
    top = df.nlargest(top_n, "test_r2")[["code", "test_r2"]].iloc[::-1]
    bottom = df.nsmallest(top_n, "test_r2")[["code", "test_r2"]].iloc[::-1]

    fig, axes = plt.subplots(1, 2, figsize=(14, 8), sharex=False)

    axes[0].barh(bottom["code"], bottom["test_r2"], color="#d62728")
    axes[0].set_title("Bottom 15 countries by test_r2")
    axes[0].set_xlabel("test_r2")
    axes[0].grid(axis="x", alpha=0.25)

    axes[1].barh(top["code"], top["test_r2"], color="#1f77b4")
    axes[1].set_title("Top 15 countries by test_r2")
    axes[1].set_xlabel("test_r2")
    axes[1].grid(axis="x", alpha=0.25)

    plt.tight_layout()
    plt.savefig(output_dir / "04_top_bottom_test_r2.png", dpi=150)
    plt.close()

    # Figure 5: gap_r2 distribution
    plt.figure(figsize=(10, 5))
    plt.hist(df["gap_r2"].clip(-5, 50).dropna(), bins=60, color="#9467bd", edgecolor="white")
    plt.title("Distribution of train_r2 - test_r2 (clipped to [-5, 50])")
    plt.xlabel("gap_r2")
    plt.ylabel("Country count")
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(output_dir / "05_gap_r2_distribution.png", dpi=150)
    plt.close()


if __name__ == "__main__":
    main()
