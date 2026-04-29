from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

from app.constants.traditional_onnx_paths import (
    TRADITIONAL_ONNX_ARTIFACTS_DIR,
    TRADITIONAL_ONNX_CASES_DATA_PATH,
    TRADITIONAL_ONNX_MODEL_REGISTRY_PATH,
    TRADITIONAL_ONNX_PANEL_DATA_PATH,
)
from app.services.traditional_onnx.traditional_onnx_utils import (
    normalize_traditional_country_key,
    parse_traditional_date,
    safe_traditional_float,
)


@dataclass(frozen=True)
class TraditionalOnnxModelSpec:
    code: str
    strategy: str
    onnx_model_path: Path
    feature_columns: tuple[str, ...]


@dataclass(frozen=True)
class TraditionalOnnxCountrySeed:
    code: str
    country_name: str
    continent: str
    latest_observation_date: date
    first_case_date: date | None
    base_features: dict[str, float]
    new_cases_history: tuple[float, ...]
    new_deaths_history: tuple[float, ...]


@dataclass(frozen=True)
class TraditionalOnnxRuntimeBundle:
    model_specs_by_code: dict[str, TraditionalOnnxModelSpec]
    global_fallback_spec: TraditionalOnnxModelSpec
    country_seeds_by_code: dict[str, TraditionalOnnxCountrySeed]
    country_code_by_normalized_name: dict[str, str]
    latest_observation_date: date


def _load_traditional_feature_columns(relative_path: str, cache: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    if relative_path in cache:
        return cache[relative_path]

    feature_path = TRADITIONAL_ONNX_ARTIFACTS_DIR / relative_path
    with feature_path.open("r", encoding="utf-8") as source_file:
        payload = json.load(source_file)

    if not isinstance(payload, list):
        raise ValueError(f"Feature columns file must be a list: {feature_path}")

    columns = tuple(str(item) for item in payload)
    cache[relative_path] = columns
    return columns


def _load_traditional_first_case_dates() -> dict[str, date]:
    if not TRADITIONAL_ONNX_CASES_DATA_PATH.exists():
        raise FileNotFoundError(f"Cases data file not found: {TRADITIONAL_ONNX_CASES_DATA_PATH}")

    first_case_by_country_key: dict[str, date] = {}

    with TRADITIONAL_ONNX_CASES_DATA_PATH.open("r", encoding="utf-8", newline="") as source_file:
        reader = csv.DictReader(source_file)
        required_columns = {"country", "date", "total_cases"}
        if reader.fieldnames is None or not required_columns.issubset(set(reader.fieldnames)):
            raise ValueError("Cases data is missing required columns: country, date, total_cases")

        for row in reader:
            total_cases = safe_traditional_float(row.get("total_cases"))
            if total_cases <= 0:
                continue

            country_name = (row.get("country") or "").strip()
            if not country_name:
                continue

            date_value = parse_traditional_date((row.get("date") or "").strip(), field_name="cases.date")
            country_key = normalize_traditional_country_key(country_name)

            existing = first_case_by_country_key.get(country_key)
            if existing is None or date_value < existing:
                first_case_by_country_key[country_key] = date_value

    return first_case_by_country_key


def _load_traditional_country_seed_data() -> tuple[
    dict[str, TraditionalOnnxCountrySeed],
    dict[str, str],
    date,
]:
    if not TRADITIONAL_ONNX_PANEL_DATA_PATH.exists():
        raise FileNotFoundError(f"Panel data file not found: {TRADITIONAL_ONNX_PANEL_DATA_PATH}")

    first_case_by_country_key = _load_traditional_first_case_dates()

    history_by_code: dict[str, list[tuple[date, float, float]]] = {}
    latest_row_by_code: dict[str, dict[str, str]] = {}
    latest_date_by_code: dict[str, date] = {}
    latest_country_name_by_code: dict[str, str] = {}

    with TRADITIONAL_ONNX_PANEL_DATA_PATH.open("r", encoding="utf-8", newline="") as source_file:
        reader = csv.DictReader(source_file)
        required_columns = {"country", "date", "new_cases", "new_deaths", "code", "continent"}
        if reader.fieldnames is None or not required_columns.issubset(set(reader.fieldnames)):
            raise ValueError(
                "Panel data is missing required columns: country, date, new_cases, new_deaths, code, continent"
            )

        for row in reader:
            code = (row.get("code") or "").strip().upper()
            if len(code) != 3:
                continue

            country_name = (row.get("country") or "").strip()
            if not country_name:
                continue

            day = parse_traditional_date((row.get("date") or "").strip(), field_name="panel.date")
            new_cases = max(0.0, safe_traditional_float(row.get("new_cases")))
            new_deaths = max(0.0, safe_traditional_float(row.get("new_deaths")))

            history_by_code.setdefault(code, []).append((day, new_cases, new_deaths))

            prev_day = latest_date_by_code.get(code)
            if prev_day is None or day >= prev_day:
                latest_date_by_code[code] = day
                latest_row_by_code[code] = dict(row)
                latest_country_name_by_code[code] = country_name

    if not latest_date_by_code:
        raise ValueError("No country records loaded from panel data.")

    country_code_by_normalized_name: dict[str, str] = {}
    country_seeds_by_code: dict[str, TraditionalOnnxCountrySeed] = {}

    for code, latest_row in latest_row_by_code.items():
        history = sorted(history_by_code.get(code, []), key=lambda item: item[0])
        if not history:
            continue

        latest_date = latest_date_by_code[code]
        country_name = latest_country_name_by_code[code]
        country_key = normalize_traditional_country_key(country_name)
        country_code_by_normalized_name[country_key] = code

        latest_28 = history[-28:]
        new_cases_history = tuple(item[1] for item in latest_28)
        new_deaths_history = tuple(item[2] for item in latest_28)

        base_features: dict[str, float] = {}
        for column_name, raw_value in latest_row.items():
            if column_name in {"country", "date", "code", "continent", "data_split", "target_next_day_new_cases"}:
                continue
            base_features[column_name] = safe_traditional_float(raw_value)

        country_seeds_by_code[code] = TraditionalOnnxCountrySeed(
            code=code,
            country_name=country_name,
            continent=(latest_row.get("continent") or "Unknown").strip() or "Unknown",
            latest_observation_date=latest_date,
            first_case_date=first_case_by_country_key.get(country_key),
            base_features=base_features,
            new_cases_history=new_cases_history,
            new_deaths_history=new_deaths_history,
        )

    latest_observation_date = max(seed.latest_observation_date for seed in country_seeds_by_code.values())
    return country_seeds_by_code, country_code_by_normalized_name, latest_observation_date


@lru_cache(maxsize=1)
def load_traditional_onnx_runtime_bundle() -> TraditionalOnnxRuntimeBundle:
    if not TRADITIONAL_ONNX_MODEL_REGISTRY_PATH.exists():
        raise FileNotFoundError(f"Traditional ONNX registry not found: {TRADITIONAL_ONNX_MODEL_REGISTRY_PATH}")

    with TRADITIONAL_ONNX_MODEL_REGISTRY_PATH.open("r", encoding="utf-8") as source_file:
        registry_payload = json.load(source_file)

    if not isinstance(registry_payload, dict):
        raise ValueError("Traditional ONNX registry payload must be a JSON object.")

    country_entries = registry_payload.get("countries")
    if not isinstance(country_entries, dict):
        raise ValueError("Traditional ONNX registry payload is missing countries map.")

    global_entry = registry_payload.get("global_fallback")
    if not isinstance(global_entry, dict):
        raise ValueError("Traditional ONNX registry payload is missing global_fallback config.")

    feature_columns_cache: dict[str, tuple[str, ...]] = {}

    global_feature_path = str(global_entry.get("feature_columns_path") or "")
    global_onnx_path = str(global_entry.get("onnx_path") or "")
    if not global_feature_path or not global_onnx_path:
        raise ValueError("Traditional ONNX global_fallback config is missing onnx_path or feature_columns_path.")

    global_fallback_spec = TraditionalOnnxModelSpec(
        code="GLOBAL",
        strategy="global_fallback",
        onnx_model_path=TRADITIONAL_ONNX_ARTIFACTS_DIR / global_onnx_path,
        feature_columns=_load_traditional_feature_columns(global_feature_path, feature_columns_cache),
    )

    model_specs_by_code: dict[str, TraditionalOnnxModelSpec] = {}
    for code, entry in country_entries.items():
        if not isinstance(entry, dict):
            continue

        upper_code = str(code).upper().strip()
        feature_path = str(entry.get("feature_columns_path") or "")
        onnx_path = str(entry.get("onnx_path") or "")
        strategy = str(entry.get("strategy") or "global_fallback")

        if not upper_code or not feature_path or not onnx_path:
            continue

        model_specs_by_code[upper_code] = TraditionalOnnxModelSpec(
            code=upper_code,
            strategy=strategy,
            onnx_model_path=TRADITIONAL_ONNX_ARTIFACTS_DIR / onnx_path,
            feature_columns=_load_traditional_feature_columns(feature_path, feature_columns_cache),
        )

    country_seeds_by_code, country_code_by_normalized_name, latest_observation_date = _load_traditional_country_seed_data()

    return TraditionalOnnxRuntimeBundle(
        model_specs_by_code=model_specs_by_code,
        global_fallback_spec=global_fallback_spec,
        country_seeds_by_code=country_seeds_by_code,
        country_code_by_normalized_name=country_code_by_normalized_name,
        latest_observation_date=latest_observation_date,
    )
