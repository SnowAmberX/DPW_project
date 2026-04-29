from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from onnxconverter_common.data_types import FloatTensorType
from onnxmltools import convert_lightgbm
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


ESSENTIAL_FEATURES = [
    "new_cases_lag_1",
    "new_cases_lag_3",
    "new_cases_lag_7",
    "new_cases_lag_14",
    "new_cases_roll_mean_7",
    "new_cases_roll_mean_14",
    "new_cases_growth_1d",
    "new_cases_growth_7d",
    "new_deaths_lag_1",
    "new_deaths_lag_7",
    "stringency_index",
    "reproduction_rate",
    "positive_rate",
    "region_peer_new_cases_roll7_mean",
    "neighbor_weighted_new_cases_mean",
    "neighbor_weighted_stringency_mean",
    "neighbor_count",
    "population",
    "population_density",
    "day_of_week",
    "month",
]


def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    valid = denominator > 0
    if not np.any(valid):
        return 0.0
    return float(np.mean(np.abs(y_true[valid] - y_pred[valid]) / denominator[valid]) * 100.0)


def evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": rmse,
        "r2": float(r2_score(y_true, y_pred)),
        "smape": smape(y_true, y_pred),
    }


def save_onnx(model: lgb.LGBMRegressor, num_features: int, output_path: Path) -> None:
    initial_types = [("input", FloatTensorType([None, num_features]))]
    onnx_model = convert_lightgbm(model, initial_types=initial_types, target_opset=15)
    output_path.write_bytes(onnx_model.SerializeToString())


def choose_feature_columns(df: pd.DataFrame) -> list[str]:
    return [col for col in ESSENTIAL_FEATURES if col in df.columns]


def build_country_target(df_country: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    raw_target = pd.to_numeric(df_country["target_next_day_new_cases"], errors="coerce").fillna(0.0).clip(lower=0.0)
    smooth_target = 0.7 * raw_target + 0.3 * raw_target.rolling(window=7, min_periods=1).mean()
    return raw_target, smooth_target


def fallback_time_split(n_rows: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    idx = np.arange(n_rows)
    train_end = max(1, int(n_rows * 0.7))
    val_end = max(train_end + 1, int(n_rows * 0.85))
    val_end = min(val_end, n_rows - 1)

    train_mask = idx < train_end
    val_mask = (idx >= train_end) & (idx < val_end)
    test_mask = idx >= val_end

    return train_mask, val_mask, test_mask


def build_split_masks(df_country: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    split_col = df_country.get("data_split")
    if split_col is None:
        train_mask, val_mask, test_mask = fallback_time_split(len(df_country))
        return train_mask, val_mask, test_mask, "auto_time_split"

    split = split_col.astype(str).str.lower()
    train_mask = (split == "train").to_numpy()
    val_mask = ((split == "validation") | (split == "val")).to_numpy()
    test_mask = (split == "test").to_numpy()

    if train_mask.sum() >= 30 and val_mask.sum() >= 10 and test_mask.sum() >= 10:
        return train_mask, val_mask, test_mask, "data_split"

    train_mask, val_mask, test_mask = fallback_time_split(len(df_country))
    return train_mask, val_mask, test_mask, "auto_time_split"


def build_train_weights(y_train: np.ndarray) -> np.ndarray:
    growth = np.abs(np.diff(np.concatenate(([y_train[0]], y_train))))
    return 1.0 + np.log1p(y_train) + 0.2 * np.log1p(growth)


def fit_lgbm(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
    sample_weight: np.ndarray,
) -> lgb.LGBMRegressor:
    objective = "poisson" if float(np.sum(y_train)) > 0 else "regression"

    model = lgb.LGBMRegressor(
        objective=objective,
        n_estimators=800,
        learning_rate=0.03,
        num_leaves=63,
        min_child_samples=20,
        subsample=0.9,
        subsample_freq=1,
        colsample_bytree=0.9,
        reg_alpha=0.05,
        reg_lambda=0.1,
        random_state=42,
        n_jobs=-1,
        verbosity=-1,
    )

    fit_kwargs: dict[str, Any] = {
        "sample_weight": sample_weight,
    }
    if len(X_val) > 0:
        fit_kwargs["eval_set"] = [(X_val, y_val)]
        fit_kwargs["eval_metric"] = "l2"
        fit_kwargs["callbacks"] = [lgb.early_stopping(stopping_rounds=80), lgb.log_evaluation(period=0)]

    model.fit(X_train, y_train, **fit_kwargs)
    return model


def train_country_model(
    code: str,
    df_country: pd.DataFrame,
    feature_cols: list[str],
    output_dir: Path,
) -> tuple[dict[str, Any] | None, str | None]:
    if len(df_country) < 40:
        return None, "too_few_rows"

    df_country = df_country.sort_values("date").reset_index(drop=True)
    raw_target, fit_target = build_country_target(df_country)

    X = df_country[feature_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).astype(np.float32)
    train_mask, val_mask, test_mask, split_mode = build_split_masks(df_country)

    if train_mask.sum() < 20 or test_mask.sum() < 5:
        return None, "insufficient_train_or_test_rows"

    X_train = X.loc[train_mask]
    y_train = fit_target.loc[train_mask].to_numpy(dtype=np.float64)

    X_val = X.loc[val_mask]
    y_val = fit_target.loc[val_mask].to_numpy(dtype=np.float64)

    X_test = X.loc[test_mask]
    y_test_raw = raw_target.loc[test_mask].to_numpy(dtype=np.float64)

    model = fit_lgbm(
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        sample_weight=build_train_weights(y_train),
    )

    train_pred = np.asarray(model.predict(X_train), dtype=np.float64)
    test_pred = np.asarray(model.predict(X_test), dtype=np.float64)

    train_pred = np.clip(train_pred, a_min=0.0, a_max=None)
    test_pred = np.clip(test_pred, a_min=0.0, a_max=None)

    train_metrics = evaluate(raw_target.loc[train_mask].to_numpy(dtype=np.float64), train_pred)
    test_metrics = evaluate(y_test_raw, test_pred)

    country_dir = output_dir / "country_models" / code
    country_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, country_dir / "lightgbm_model.joblib")
    save_onnx(model, len(feature_cols), country_dir / "lightgbm_model.onnx")
    (country_dir / "feature_columns.json").write_text(json.dumps(feature_cols, indent=2), encoding="utf-8")
    (country_dir / "inference_preprocess.json").write_text(
        json.dumps(
            {
                "target": "smoothed_next_day_new_cases",
                "postprocess": "clip_to_non_negative",
                "note": "features include regional and neighbor weighted signals",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "code": code,
        "split_mode": split_mode,
        "train_rows": int(train_mask.sum()),
        "val_rows": int(val_mask.sum()),
        "test_rows": int(test_mask.sum()),
        "num_features": len(feature_cols),
        "best_iteration": int(getattr(model, "best_iteration_", model.n_estimators)),
        "train_r2": train_metrics["r2"],
        "test_r2": test_metrics["r2"],
        "test_rmse": test_metrics["rmse"],
        "test_smape": test_metrics["smape"],
    }, None


def train_global_fallback(
    df: pd.DataFrame,
    feature_cols: list[str],
    output_dir: Path,
) -> dict[str, Any]:
    df_all = df.sort_values(["date", "code"]).reset_index(drop=True)
    raw_target = pd.to_numeric(df_all["target_next_day_new_cases"], errors="coerce").fillna(0.0).clip(lower=0.0)
    fit_target = 0.7 * raw_target + 0.3 * raw_target.rolling(window=7, min_periods=1).mean()

    X_num = df_all[feature_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).astype(np.float32)
    X_code = pd.get_dummies(df_all["code"].astype(str), prefix="code", dtype=np.float32)
    X = pd.concat([X_num, X_code], axis=1)

    train_mask, val_mask, test_mask, split_mode = build_split_masks(df_all)

    X_train = X.loc[train_mask]
    y_train = fit_target.loc[train_mask].to_numpy(dtype=np.float64)
    X_val = X.loc[val_mask]
    y_val = fit_target.loc[val_mask].to_numpy(dtype=np.float64)
    X_test = X.loc[test_mask]

    model = fit_lgbm(
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        sample_weight=build_train_weights(y_train),
    )

    test_pred = np.asarray(model.predict(X_test), dtype=np.float64)
    test_pred = np.clip(test_pred, a_min=0.0, a_max=None)

    test_metrics = evaluate(raw_target.loc[test_mask].to_numpy(dtype=np.float64), test_pred)

    fallback_dir = output_dir / "global_fallback_model"
    fallback_dir.mkdir(parents=True, exist_ok=True)

    feature_cols_global = list(X.columns)
    joblib.dump(model, fallback_dir / "lightgbm_model.joblib")
    save_onnx(model, len(feature_cols_global), fallback_dir / "lightgbm_model.onnx")
    (fallback_dir / "feature_columns.json").write_text(json.dumps(feature_cols_global, indent=2), encoding="utf-8")
    (fallback_dir / "inference_preprocess.json").write_text(
        json.dumps(
            {
                "target": "smoothed_next_day_new_cases",
                "postprocess": "clip_to_non_negative",
                "split_mode": split_mode,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    metrics = {
        "split_mode": split_mode,
        "train_rows": int(train_mask.sum()),
        "val_rows": int(val_mask.sum()),
        "test_rows": int(test_mask.sum()),
        "num_features": len(feature_cols_global),
        "test_r2": test_metrics["r2"],
        "test_rmse": test_metrics["rmse"],
        "test_smape": test_metrics["smape"],
    }
    (output_dir / "global_fallback_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def write_registry(
    selected_codes: list[str],
    trained_codes: set[str],
    skipped_reason: dict[str, str],
    output_dir: Path,
    global_metrics: dict[str, Any],
) -> None:
    countries: dict[str, Any] = {}
    for code in selected_codes:
        if code in trained_codes:
            countries[code] = {
                "strategy": "country_model",
                "reason": "trained",
                "onnx_path": f"country_models/{code}/lightgbm_model.onnx",
                "joblib_path": f"country_models/{code}/lightgbm_model.joblib",
                "feature_columns_path": f"country_models/{code}/feature_columns.json",
            }
        else:
            countries[code] = {
                "strategy": "global_fallback",
                "reason": skipped_reason.get(code, "training_failed"),
                "onnx_path": "global_fallback_model/lightgbm_model.onnx",
                "joblib_path": "global_fallback_model/lightgbm_model.joblib",
                "feature_columns_path": "global_fallback_model/feature_columns.json",
            }

    payload = {
        "model_version": "country_v5_simple_epicurve",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "global_fallback": {
            "onnx_path": "global_fallback_model/lightgbm_model.onnx",
            "joblib_path": "global_fallback_model/lightgbm_model.joblib",
            "feature_columns_path": "global_fallback_model/feature_columns.json",
            "metrics": {
                "test_r2": float(global_metrics["test_r2"]),
                "test_rmse": float(global_metrics["test_rmse"]),
                "test_smape": float(global_metrics["test_smape"]),
            },
        },
        "countries": countries,
    }
    (output_dir / "model_registry.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_reports(
    metrics_df: pd.DataFrame,
    skipped_reason: dict[str, str],
    output_dir: Path,
) -> None:
    metrics_df.to_csv(output_dir / "country_metrics.csv", index=False)
    (output_dir / "country_metrics.json").write_text(
        metrics_df.to_json(orient="records", force_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "skipped_countries.txt").write_text(
        "\n".join(f"{code}: {reason}" for code, reason in sorted(skipped_reason.items())),
        encoding="utf-8",
    )

    if metrics_df.empty:
        summary = "No country model was trained."
    else:
        summary = "\n".join(
            [
                "Simple Country Model Training Summary",
                f"trained_countries: {len(metrics_df)}",
                f"mean_test_r2: {metrics_df['test_r2'].mean():.4f}",
                f"mean_test_rmse: {metrics_df['test_rmse'].mean():.4f}",
                f"mean_test_smape: {metrics_df['test_smape'].mean():.2f}%",
                "",
                "Top 10 by test_r2:",
            ]
            + [
                f"- {row.code}: r2={row.test_r2:.4f}, rmse={row.test_rmse:.4f}, smape={row.test_smape:.2f}%"
                for row in metrics_df.sort_values("test_r2", ascending=False).head(10).itertuples(index=False)
            ]
        )

    (output_dir / "summary.txt").write_text(summary, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train simple per-country LightGBM ONNX models with regional influence")
    parser.add_argument(
        "--data",
        type=str,
        default=str(Path(__file__).resolve().parents[1] / "data" / "processed_data" / "cleaned_panel_country_day.csv"),
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(Path(__file__).resolve().parent / "model" / "artifacts_country_v4_simple"),
    )
    parser.add_argument("--countries", type=str, default="", help="Comma separated ISO3 list. Empty means all.")
    args = parser.parse_args()

    data_path = Path(args.data).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(data_path)
    df["code"] = df["code"].astype(str).str.upper().str.strip()
    df = df[df["code"].str.match(r"^[A-Z]{3}$", na=False)].copy()

    needed_cols = {"code", "date", "target_next_day_new_cases"}
    missing = sorted([c for c in needed_cols if c not in df.columns])
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    feature_cols = choose_feature_columns(df)
    if not feature_cols:
        raise ValueError("No essential features found in data.")

    if args.countries.strip():
        selected_codes = sorted({c.strip().upper() for c in args.countries.split(",") if c.strip()})
    else:
        selected_codes = sorted(df["code"].unique().tolist())

    metrics_rows: list[dict[str, Any]] = []
    skipped_reason: dict[str, str] = {}

    for index, code in enumerate(selected_codes, start=1):
        print(f"[{index}/{len(selected_codes)}] training {code}")
        df_country = df[df["code"] == code].copy()
        metrics, reason = train_country_model(code, df_country, feature_cols, output_dir)
        if metrics is None:
            skipped_reason[code] = reason or "unknown"
            continue
        metrics_rows.append(metrics)

    metrics_df = pd.DataFrame(metrics_rows).sort_values("code").reset_index(drop=True) if metrics_rows else pd.DataFrame()
    trained_codes = set(metrics_df["code"].tolist()) if not metrics_df.empty else set()

    global_metrics = train_global_fallback(df=df, feature_cols=feature_cols, output_dir=output_dir)

    write_reports(metrics_df=metrics_df, skipped_reason=skipped_reason, output_dir=output_dir)
    write_registry(
        selected_codes=selected_codes,
        trained_codes=trained_codes,
        skipped_reason=skipped_reason,
        output_dir=output_dir,
        global_metrics=global_metrics,
    )

    result_lines = [
        "Simple ONNX Training Result",
        f"selected_countries: {len(selected_codes)}",
        f"trained_country_models: {len(trained_codes)}",
        f"fallback_countries: {len(selected_codes) - len(trained_codes)}",
        f"global_test_r2: {global_metrics['test_r2']:.4f}",
        f"global_test_smape: {global_metrics['test_smape']:.2f}%",
        "",
        "Notes:",
        "- Features keep regional and neighbor influence.",
        "- Target uses smoothed next-day cases to better capture epidemic phases.",
    ]
    (output_dir / "result.txt").write_text("\n".join(result_lines), encoding="utf-8")

    print(f"saved: {output_dir}")
    print(f"trained countries: {len(trained_codes)} / {len(selected_codes)}")


if __name__ == "__main__":
    main()
