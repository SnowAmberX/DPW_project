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


def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    valid = denominator != 0
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


def prepare_xy(
    df_data: pd.DataFrame,
    drop_cols: list[str],
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    X = df_data.drop(columns=[c for c in drop_cols if c in df_data.columns]).copy()
    y = pd.to_numeric(df_data["target_next_day_new_cases"], errors="coerce").fillna(0)
    split = df_data["data_split"].astype(str)

    object_cols = X.select_dtypes(include=["object", "string"]).columns.tolist()
    if object_cols:
        X = pd.get_dummies(X, columns=object_cols, dummy_na=False, dtype=np.float32)

    X = X.apply(pd.to_numeric, errors="coerce").fillna(0).astype(np.float32)
    return X, y, split


def train_lgb_model(
    X_train: pd.DataFrame,
    y_train_fit: np.ndarray,
    X_val: pd.DataFrame,
    y_val_fit: np.ndarray,
    sample_weight: np.ndarray,
) -> lgb.LGBMRegressor:
    model = lgb.LGBMRegressor(
        objective="regression",
        metric="rmse",
        n_estimators=1100,
        learning_rate=0.025,
        num_leaves=63,
        min_child_samples=20,
        subsample=0.9,
        subsample_freq=1,
        colsample_bytree=0.9,
        reg_alpha=0.08,
        reg_lambda=0.15,
        random_state=42,
        n_jobs=-1,
        verbosity=-1,
    )

    model.fit(
        X_train,
        y_train_fit,
        sample_weight=sample_weight,
        eval_set=[(X_val, y_val_fit)],
        eval_metric="l2",
        callbacks=[lgb.early_stopping(stopping_rounds=100), lgb.log_evaluation(period=0)],
    )
    return model


def build_train_weights(y_train: pd.Series) -> np.ndarray:
    y_arr = y_train.to_numpy(dtype=np.float64)
    volume_weight = 1.0 + np.log1p(y_arr)
    recency_weight = np.linspace(1.0, 1.8, num=len(y_arr), dtype=np.float64)
    return volume_weight * recency_weight


def train_country_model(
    country_code: str,
    df_country: pd.DataFrame,
    output_models_dir: Path,
    min_train_rows: int,
    min_val_rows: int,
    min_test_rows: int,
) -> tuple[dict[str, Any] | None, str | None]:
    df_country = df_country.sort_values("date").reset_index(drop=True)
    X, y, split = prepare_xy(
        df_country,
        drop_cols=["target_next_day_new_cases", "data_split", "date", "country", "code"],
    )

    train_mask = split == "train"
    val_mask = split == "validation"
    test_mask = split == "test"

    train_n = int(train_mask.sum())
    val_n = int(val_mask.sum())
    test_n = int(test_mask.sum())

    if train_n < min_train_rows or val_n < min_val_rows or test_n < min_test_rows:
        reason = f"insufficient_split_rows(train={train_n},val={val_n},test={test_n})"
        return None, reason

    X_train, y_train = X.loc[train_mask], y.loc[train_mask]
    X_val, y_val = X.loc[val_mask], y.loc[val_mask]
    X_test, y_test = X.loc[test_mask], y.loc[test_mask]

    # Remove train-constant columns to reduce useless dimensions.
    variable_cols = [c for c in X_train.columns if X_train[c].nunique(dropna=False) > 1]
    if not variable_cols:
        return None, "no_variable_features"

    X_train = X_train[variable_cols]
    X_val = X_val[variable_cols]
    X_test = X_test[variable_cols]

    y_train_fit = np.log1p(y_train.to_numpy(dtype=np.float64))
    y_val_fit = np.log1p(y_val.to_numpy(dtype=np.float64))
    sample_weight = build_train_weights(y_train)

    model = train_lgb_model(X_train, y_train_fit, X_val, y_val_fit, sample_weight)

    val_pred = np.expm1(np.asarray(model.predict(X_val), dtype=np.float64))
    test_pred = np.expm1(np.asarray(model.predict(X_test), dtype=np.float64))
    train_pred = np.expm1(np.asarray(model.predict(X_train), dtype=np.float64))

    val_pred = np.clip(val_pred, a_min=0, a_max=None)
    test_pred = np.clip(test_pred, a_min=0, a_max=None)
    train_pred = np.clip(train_pred, a_min=0, a_max=None)

    val_metrics = evaluate(y_val.to_numpy(dtype=np.float64), val_pred)
    test_metrics = evaluate(y_test.to_numpy(dtype=np.float64), test_pred)
    train_metrics = evaluate(y_train.to_numpy(dtype=np.float64), train_pred)

    model_dir = output_models_dir / country_code
    model_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, model_dir / "lightgbm_model.joblib")
    save_onnx(model, len(variable_cols), model_dir / "lightgbm_model.onnx")
    (model_dir / "feature_columns.json").write_text(json.dumps(variable_cols, indent=2), encoding="utf-8")
    (model_dir / "inference_preprocess.json").write_text(
        json.dumps(
            {
                "selected_target_transform": "log1p",
                "postprocess": "apply expm1 and clip at 0",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "code": country_code,
        "train_rows": int(X_train.shape[0]),
        "val_rows": int(X_val.shape[0]),
        "test_rows": int(X_test.shape[0]),
        "num_features": int(len(variable_cols)),
        "best_iteration": int(getattr(model, "best_iteration_", model.n_estimators)),
        "train_mae": train_metrics["mae"],
        "train_rmse": train_metrics["rmse"],
        "train_r2": train_metrics["r2"],
        "val_mae": val_metrics["mae"],
        "val_rmse": val_metrics["rmse"],
        "val_r2": val_metrics["r2"],
        "test_mae": test_metrics["mae"],
        "test_rmse": test_metrics["rmse"],
        "test_r2": test_metrics["r2"],
        "test_smape": test_metrics["smape"],
    }, None


def train_global_fallback_model(
    df: pd.DataFrame,
    output_dir: Path,
    min_train_rows: int,
    min_val_rows: int,
    min_test_rows: int,
) -> dict[str, Any]:
    df_global = df.sort_values(["date", "code"]).reset_index(drop=True)
    X, y, split = prepare_xy(
        df_global,
        drop_cols=["target_next_day_new_cases", "data_split", "date", "country"],
    )

    train_mask = split == "train"
    val_mask = split == "validation"
    test_mask = split == "test"

    train_n = int(train_mask.sum())
    val_n = int(val_mask.sum())
    test_n = int(test_mask.sum())

    if train_n < min_train_rows or val_n < min_val_rows or test_n < min_test_rows:
        raise RuntimeError(
            f"Global fallback model does not have enough rows: train={train_n}, val={val_n}, test={test_n}"
        )

    X_train, y_train = X.loc[train_mask], y.loc[train_mask]
    X_val, y_val = X.loc[val_mask], y.loc[val_mask]
    X_test, y_test = X.loc[test_mask], y.loc[test_mask]

    variable_cols = [c for c in X_train.columns if X_train[c].nunique(dropna=False) > 1]
    if not variable_cols:
        raise RuntimeError("Global fallback model has no variable features.")

    X_train = X_train[variable_cols]
    X_val = X_val[variable_cols]
    X_test = X_test[variable_cols]

    y_train_fit = np.log1p(y_train.to_numpy(dtype=np.float64))
    y_val_fit = np.log1p(y_val.to_numpy(dtype=np.float64))
    sample_weight = build_train_weights(y_train)

    model = train_lgb_model(X_train, y_train_fit, X_val, y_val_fit, sample_weight)

    train_pred = np.expm1(np.asarray(model.predict(X_train), dtype=np.float64))
    val_pred = np.expm1(np.asarray(model.predict(X_val), dtype=np.float64))
    test_pred = np.expm1(np.asarray(model.predict(X_test), dtype=np.float64))

    train_pred = np.clip(train_pred, a_min=0, a_max=None)
    val_pred = np.clip(val_pred, a_min=0, a_max=None)
    test_pred = np.clip(test_pred, a_min=0, a_max=None)

    train_metrics = evaluate(y_train.to_numpy(dtype=np.float64), train_pred)
    val_metrics = evaluate(y_val.to_numpy(dtype=np.float64), val_pred)
    test_metrics = evaluate(y_test.to_numpy(dtype=np.float64), test_pred)

    model_dir = output_dir / "global_fallback_model"
    model_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, model_dir / "lightgbm_model.joblib")
    save_onnx(model, len(variable_cols), model_dir / "lightgbm_model.onnx")
    (model_dir / "feature_columns.json").write_text(json.dumps(variable_cols, indent=2), encoding="utf-8")
    (model_dir / "inference_preprocess.json").write_text(
        json.dumps(
            {
                "selected_target_transform": "log1p",
                "postprocess": "apply expm1 and clip at 0",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    metrics = {
        "train_rows": int(X_train.shape[0]),
        "val_rows": int(X_val.shape[0]),
        "test_rows": int(X_test.shape[0]),
        "num_features": int(len(variable_cols)),
        "best_iteration": int(getattr(model, "best_iteration_", model.n_estimators)),
        "train_mae": train_metrics["mae"],
        "train_rmse": train_metrics["rmse"],
        "train_r2": train_metrics["r2"],
        "val_mae": val_metrics["mae"],
        "val_rmse": val_metrics["rmse"],
        "val_r2": val_metrics["r2"],
        "test_mae": test_metrics["mae"],
        "test_rmse": test_metrics["rmse"],
        "test_r2": test_metrics["r2"],
        "test_smape": test_metrics["smape"],
        "onnx_path": str((model_dir / "lightgbm_model.onnx").relative_to(output_dir)),
        "joblib_path": str((model_dir / "lightgbm_model.joblib").relative_to(output_dir)),
    }

    (output_dir / "global_fallback_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def write_summary(metrics_df: pd.DataFrame, summary_path: Path) -> None:
    if metrics_df.empty:
        summary_path.write_text("No country model trained.", encoding="utf-8")
        return

    weighted = metrics_df["test_rows"]
    weighted_rmse = float(np.average(metrics_df["test_rmse"], weights=weighted))
    weighted_mae = float(np.average(metrics_df["test_mae"], weights=weighted))
    weighted_smape = float(np.average(metrics_df["test_smape"], weights=weighted))

    lines = [
        "Country-Specific LightGBM Summary",
        f"Trained countries: {len(metrics_df)}",
        "",
        "Test Metrics (Unweighted Mean):",
        f"- MAE: {metrics_df['test_mae'].mean():.4f}",
        f"- RMSE: {metrics_df['test_rmse'].mean():.4f}",
        f"- R2: {metrics_df['test_r2'].mean():.4f}",
        f"- SMAPE: {metrics_df['test_smape'].mean():.4f}%",
        "",
        "Test Metrics (Weighted by Test Rows):",
        f"- MAE: {weighted_mae:.4f}",
        f"- RMSE: {weighted_rmse:.4f}",
        f"- SMAPE: {weighted_smape:.4f}%",
        "",
        "Top 10 Countries by Highest Test R2:",
    ]

    best = metrics_df.sort_values("test_r2", ascending=False).head(10)
    for _, row in best.iterrows():
        lines.append(
            f"- {row['code']}: R2={row['test_r2']:.4f}, RMSE={row['test_rmse']:.4f}, SMAPE={row['test_smape']:.2f}%"
        )

    lines.append("")
    lines.append("Worst 10 Countries by Lowest Test R2:")
    worst = metrics_df.sort_values("test_r2", ascending=True).head(10)
    for _, row in worst.iterrows():
        lines.append(
            f"- {row['code']}: R2={row['test_r2']:.4f}, RMSE={row['test_rmse']:.4f}, SMAPE={row['test_smape']:.2f}%"
        )

    summary_path.write_text("\n".join(lines), encoding="utf-8")


def choose_serving_strategy(
    row: pd.Series,
    serving_min_r2: float,
    serving_max_smape: float,
) -> tuple[str, str]:
    r2 = float(row["test_r2"])
    smape_val = float(row["test_smape"])

    if not np.isfinite(r2) or not np.isfinite(smape_val):
        return "global_fallback", "invalid_metrics"
    if abs(r2) < 1e-12 and smape_val >= 199.9:
        return "global_fallback", "degenerate_country_model"
    if r2 < serving_min_r2:
        return "global_fallback", f"r2_below_threshold({r2:.4f}<{serving_min_r2:.4f})"
    if smape_val > serving_max_smape:
        return "global_fallback", f"smape_above_threshold({smape_val:.2f}>{serving_max_smape:.2f})"
    return "country_model", "passed_quality_gate"


def build_serving_plan(
    selected_codes: list[str],
    metrics_df: pd.DataFrame,
    skipped_reason: dict[str, str],
    output_dir: Path,
    serving_min_r2: float,
    serving_max_smape: float,
) -> pd.DataFrame:
    metrics_map: dict[str, pd.Series] = {
        str(row["code"]).upper(): row for _, row in metrics_df.iterrows()
    }

    rows: list[dict[str, Any]] = []
    for code in selected_codes:
        upper_code = str(code).upper()
        if upper_code in metrics_map:
            row = metrics_map[upper_code]
            strategy, reason = choose_serving_strategy(row, serving_min_r2, serving_max_smape)
            rows.append(
                {
                    "code": upper_code,
                    "strategy": strategy,
                    "reason": reason,
                    "train_rows": int(row["train_rows"]),
                    "val_rows": int(row["val_rows"]),
                    "test_rows": int(row["test_rows"]),
                    "test_r2": float(row["test_r2"]),
                    "test_smape": float(row["test_smape"]),
                    "onnx_path": (
                        f"country_models/{upper_code}/lightgbm_model.onnx"
                        if strategy == "country_model"
                        else "global_fallback_model/lightgbm_model.onnx"
                    ),
                    "joblib_path": (
                        f"country_models/{upper_code}/lightgbm_model.joblib"
                        if strategy == "country_model"
                        else "global_fallback_model/lightgbm_model.joblib"
                    ),
                    "feature_columns_path": (
                        f"country_models/{upper_code}/feature_columns.json"
                        if strategy == "country_model"
                        else "global_fallback_model/feature_columns.json"
                    ),
                }
            )
            continue

        rows.append(
            {
                "code": upper_code,
                "strategy": "global_fallback",
                "reason": skipped_reason.get(upper_code, "country_model_not_trained"),
                "train_rows": 0,
                "val_rows": 0,
                "test_rows": 0,
                "test_r2": np.nan,
                "test_smape": np.nan,
                "onnx_path": "global_fallback_model/lightgbm_model.onnx",
                "joblib_path": "global_fallback_model/lightgbm_model.joblib",
                "feature_columns_path": "global_fallback_model/feature_columns.json",
            }
        )

    plan_df = pd.DataFrame(rows).sort_values("code").reset_index(drop=True)
    plan_df.to_csv(output_dir / "country_serving_plan.csv", index=False)
    (output_dir / "country_serving_plan.json").write_text(
        plan_df.to_json(orient="records", force_ascii=False, indent=2),
        encoding="utf-8",
    )
    return plan_df


def write_result_txt(
    output_dir: Path,
    selected_codes: list[str],
    metrics_df: pd.DataFrame,
    skipped_reason: dict[str, str],
    plan_df: pd.DataFrame,
    global_metrics: dict[str, Any],
    serving_min_r2: float,
    serving_max_smape: float,
) -> None:
    trained_count = int(len(metrics_df))
    skipped_count = int(len(skipped_reason))
    country_model_count = int((plan_df["strategy"] == "country_model").sum())
    fallback_count = int((plan_df["strategy"] == "global_fallback").sum())

    if metrics_df.empty:
        mean_r2 = float("nan")
        mean_smape = float("nan")
    else:
        mean_r2 = float(metrics_df["test_r2"].mean())
        mean_smape = float(metrics_df["test_smape"].mean())

    lines = [
        "Country Forecast Training Result",
        f"generated_at_utc: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "[Training Coverage]",
        f"selected_countries: {len(selected_codes)}",
        f"trained_country_models: {trained_count}",
        f"skipped_country_models: {skipped_count}",
        "",
        "[Country Model Quality]",
        f"mean_test_r2: {mean_r2:.4f}",
        f"mean_test_smape: {mean_smape:.4f}%",
        "",
        "[Global Fallback Model Quality]",
        f"global_test_r2: {global_metrics['test_r2']:.4f}",
        f"global_test_rmse: {global_metrics['test_rmse']:.4f}",
        f"global_test_smape: {global_metrics['test_smape']:.4f}%",
        "",
        "[Serving Gate]",
        f"country_model_gate: test_r2 >= {serving_min_r2:.3f} and test_smape <= {serving_max_smape:.3f}",
        f"country_model_used: {country_model_count}",
        f"global_fallback_used: {fallback_count}",
        "",
        "[Deployment Files]",
        "- model_registry.json",
        "- country_serving_plan.csv",
        "- country_serving_plan.json",
        "- global_fallback_model/lightgbm_model.onnx",
        "- global_fallback_model/lightgbm_model.joblib",
        "- country_models/<ISO3>/lightgbm_model.onnx",
        "- country_models/<ISO3>/lightgbm_model.joblib",
        "",
        "[Skipped Countries]",
    ]

    if skipped_reason:
        for code in sorted(skipped_reason.keys()):
            lines.append(f"- {code}: {skipped_reason[code]}")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("[Fallback Reason Distribution]")
    fallback_reason_counts = (
        plan_df[plan_df["strategy"] == "global_fallback"]["reason"].value_counts(dropna=False).to_dict()
    )
    if fallback_reason_counts:
        for reason, cnt in sorted(fallback_reason_counts.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"- {reason}: {cnt}")
    else:
        lines.append("- None")

    (output_dir / "result.txt").write_text("\n".join(lines), encoding="utf-8")


def write_model_registry(
    output_dir: Path,
    plan_df: pd.DataFrame,
    global_metrics: dict[str, Any],
    serving_min_r2: float,
    serving_max_smape: float,
) -> None:
    countries: dict[str, Any] = {}
    for _, row in plan_df.iterrows():
        code = str(row["code"]).upper()
        countries[code] = {
            "strategy": row["strategy"],
            "reason": row["reason"],
            "onnx_path": row["onnx_path"],
            "joblib_path": row["joblib_path"],
            "feature_columns_path": row["feature_columns_path"],
        }

    registry = {
        "model_version": "country_v4_with_global_fallback",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "default_strategy": "global_fallback",
        "serving_gate": {
            "min_test_r2": serving_min_r2,
            "max_test_smape": serving_max_smape,
        },
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

    (output_dir / "model_registry.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train one LightGBM model per country with deployable fallback")
    parser.add_argument(
        "--data",
        type=str,
        default=str(Path(__file__).resolve().parents[1] / "data" / "processed_data" / "cleaned_panel_country_day.csv"),
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(Path(__file__).resolve().parent / "artifacts_country_v3"),
    )
    parser.add_argument(
        "--countries",
        type=str,
        default="",
        help="Optional comma-separated ISO3 codes. Empty means all countries.",
    )
    parser.add_argument(
        "--max-countries",
        type=int,
        default=0,
        help="Optional cap for debugging; 0 means no cap.",
    )
    parser.add_argument("--min-train-rows", type=int, default=365)
    parser.add_argument("--min-val-rows", type=int, default=60)
    parser.add_argument("--min-test-rows", type=int, default=60)
    parser.add_argument("--serving-min-r2", type=float, default=0.10)
    parser.add_argument("--serving-max-smape", type=float, default=190.0)
    args = parser.parse_args()

    data_path = Path(args.data).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_models_dir = output_dir / "country_models"
    output_models_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(data_path)
    df["code"] = df["code"].astype(str).str.upper().str.strip()
    df = df[df["code"].str.match(r"^[A-Z]{3}$", na=False)].copy()

    required = {"code", "data_split", "target_next_day_new_cases", "date"}
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns for training: {missing}")

    if args.countries.strip():
        selected_codes = [c.strip().upper() for c in args.countries.split(",") if c.strip()]
    else:
        selected_codes = sorted(df["code"].dropna().astype(str).str.upper().unique().tolist())

    if args.max_countries > 0:
        selected_codes = selected_codes[: args.max_countries]

    metrics_rows: list[dict[str, Any]] = []
    skipped_reason: dict[str, str] = {}

    for idx, code in enumerate(selected_codes, start=1):
        df_country = df[df["code"].astype(str).str.upper() == code].copy()
        if df_country.empty:
            skipped_reason[code] = "missing_country_data"
            continue

        print(f"[{idx}/{len(selected_codes)}] Training country model: {code}")
        result, reason = train_country_model(
            country_code=code,
            df_country=df_country,
            output_models_dir=output_models_dir,
            min_train_rows=args.min_train_rows,
            min_val_rows=args.min_val_rows,
            min_test_rows=args.min_test_rows,
        )
        if result is None:
            skipped_reason[code] = reason or "unknown_skip_reason"
            continue
        metrics_rows.append(result)

    metrics_df = pd.DataFrame(metrics_rows)
    if not metrics_df.empty:
        metrics_df = metrics_df.sort_values("code").reset_index(drop=True)

    metrics_csv = output_dir / "country_metrics.csv"
    metrics_json = output_dir / "country_metrics.json"
    summary_txt = output_dir / "summary.txt"
    skipped_txt = output_dir / "skipped_countries.txt"

    metrics_df.to_csv(metrics_csv, index=False)
    metrics_json.write_text(metrics_df.to_json(orient="records", force_ascii=False, indent=2), encoding="utf-8")
    write_summary(metrics_df, summary_txt)
    skipped_txt.write_text(
        "\n".join([f"{k}: {v}" for k, v in sorted(skipped_reason.items())]),
        encoding="utf-8",
    )

    global_metrics = train_global_fallback_model(
        df=df,
        output_dir=output_dir,
        min_train_rows=max(args.min_train_rows, 1000),
        min_val_rows=max(args.min_val_rows, 200),
        min_test_rows=max(args.min_test_rows, 200),
    )

    plan_df = build_serving_plan(
        selected_codes=selected_codes,
        metrics_df=metrics_df,
        skipped_reason=skipped_reason,
        output_dir=output_dir,
        serving_min_r2=args.serving_min_r2,
        serving_max_smape=args.serving_max_smape,
    )

    write_model_registry(
        output_dir=output_dir,
        plan_df=plan_df,
        global_metrics=global_metrics,
        serving_min_r2=args.serving_min_r2,
        serving_max_smape=args.serving_max_smape,
    )

    write_result_txt(
        output_dir=output_dir,
        selected_codes=selected_codes,
        metrics_df=metrics_df,
        skipped_reason=skipped_reason,
        plan_df=plan_df,
        global_metrics=global_metrics,
        serving_min_r2=args.serving_min_r2,
        serving_max_smape=args.serving_max_smape,
    )

    print(f"Saved metrics CSV: {metrics_csv}")
    print(f"Saved metrics JSON: {metrics_json}")
    print(f"Saved summary: {summary_txt}")
    print(f"Saved skipped country list: {skipped_txt}")
    print(f"Saved global fallback metrics: {output_dir / 'global_fallback_metrics.json'}")
    print(f"Saved serving plan CSV: {output_dir / 'country_serving_plan.csv'}")
    print(f"Saved serving plan JSON: {output_dir / 'country_serving_plan.json'}")
    print(f"Saved model registry: {output_dir / 'model_registry.json'}")
    print(f"Saved final result file: {output_dir / 'result.txt'}")
    print(f"Selected countries: {len(selected_codes)} | Trained country models: {len(metrics_df)} | Skipped: {len(skipped_reason)}")


if __name__ == "__main__":
    main()
