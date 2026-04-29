from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import date

import numpy as np

from app.services.traditional_onnx.traditional_onnx_repository import TraditionalOnnxCountrySeed


@dataclass
class TraditionalOnnxCountryRuntimeState:
    code: str
    country_name: str
    continent: str
    first_case_date: date | None
    base_features: dict[str, float]
    new_cases_history: deque[float]
    new_deaths_history: deque[float]


@dataclass(frozen=True)
class TraditionalOnnxDynamicFeatureContext:
    global_new_cases_mean: float
    continent_new_cases_mean: dict[str, float]


def create_traditional_onnx_runtime_states(
    country_seeds_by_code: dict[str, TraditionalOnnxCountrySeed],
) -> dict[str, TraditionalOnnxCountryRuntimeState]:
    states: dict[str, TraditionalOnnxCountryRuntimeState] = {}
    for code, seed in country_seeds_by_code.items():
        cases_history = list(seed.new_cases_history) if seed.new_cases_history else [0.0]
        deaths_history = list(seed.new_deaths_history) if seed.new_deaths_history else [0.0]

        states[code] = TraditionalOnnxCountryRuntimeState(
            code=code,
            country_name=seed.country_name,
            continent=seed.continent,
            first_case_date=seed.first_case_date,
            base_features=dict(seed.base_features),
            new_cases_history=deque(cases_history, maxlen=28),
            new_deaths_history=deque(deaths_history, maxlen=28),
        )

    return states


def build_traditional_onnx_dynamic_feature_context(
    states_by_code: dict[str, TraditionalOnnxCountryRuntimeState],
) -> TraditionalOnnxDynamicFeatureContext:
    continent_cases: dict[str, list[float]] = {}
    all_cases: list[float] = []

    for state in states_by_code.values():
        latest_cases = float(state.new_cases_history[-1]) if state.new_cases_history else 0.0
        all_cases.append(latest_cases)
        continent_cases.setdefault(state.continent, []).append(latest_cases)

    global_mean = float(np.mean(all_cases)) if all_cases else 0.0
    continent_means = {
        continent: float(np.mean(values)) if values else 0.0
        for continent, values in continent_cases.items()
    }

    return TraditionalOnnxDynamicFeatureContext(
        global_new_cases_mean=global_mean,
        continent_new_cases_mean=continent_means,
    )


def _traditional_lag(history: deque[float], steps: int) -> float:
    if not history:
        return 0.0
    if steps <= 1:
        return float(history[-1])

    index = len(history) - steps
    if index < 0:
        return float(history[0])

    return float(history[index])


def _traditional_mean_of_last(history: deque[float], window: int) -> float:
    if not history:
        return 0.0
    values = list(history)[-window:]
    if not values:
        return 0.0
    return float(np.mean(values))


def _traditional_growth(numerator: float, denominator: float) -> float:
    if abs(denominator) < 1e-6:
        return 0.0
    return float((numerator - denominator) / abs(denominator))


def build_traditional_onnx_feature_vector(
    state: TraditionalOnnxCountryRuntimeState,
    feature_columns: tuple[str, ...],
    feature_date: date,
    dynamic_context: TraditionalOnnxDynamicFeatureContext,
) -> np.ndarray:
    feature_values: dict[str, float] = dict(state.base_features)

    latest_cases = _traditional_lag(state.new_cases_history, 1)
    latest_deaths = _traditional_lag(state.new_deaths_history, 1)

    feature_values["new_cases"] = latest_cases
    feature_values["new_deaths"] = latest_deaths

    feature_values["new_cases_lag_1"] = _traditional_lag(state.new_cases_history, 1)
    feature_values["new_cases_lag_3"] = _traditional_lag(state.new_cases_history, 3)
    feature_values["new_cases_lag_7"] = _traditional_lag(state.new_cases_history, 7)
    feature_values["new_cases_lag_14"] = _traditional_lag(state.new_cases_history, 14)

    feature_values["new_deaths_lag_1"] = _traditional_lag(state.new_deaths_history, 1)
    feature_values["new_deaths_lag_3"] = _traditional_lag(state.new_deaths_history, 3)
    feature_values["new_deaths_lag_7"] = _traditional_lag(state.new_deaths_history, 7)
    feature_values["new_deaths_lag_14"] = _traditional_lag(state.new_deaths_history, 14)

    feature_values["new_cases_roll_mean_7"] = _traditional_mean_of_last(state.new_cases_history, 7)
    feature_values["new_cases_roll_mean_14"] = _traditional_mean_of_last(state.new_cases_history, 14)

    feature_values["new_cases_growth_1d"] = _traditional_growth(
        _traditional_lag(state.new_cases_history, 1),
        _traditional_lag(state.new_cases_history, 2),
    )
    feature_values["new_cases_growth_7d"] = _traditional_growth(
        _traditional_lag(state.new_cases_history, 1),
        _traditional_lag(state.new_cases_history, 8),
    )

    continent_mean = dynamic_context.continent_new_cases_mean.get(
        state.continent,
        dynamic_context.global_new_cases_mean,
    )
    feature_values["region_peer_new_cases_roll7_mean"] = continent_mean
    feature_values["neighbor_weighted_new_cases_mean"] = dynamic_context.global_new_cases_mean

    feature_values.setdefault("neighbor_weighted_stringency_mean", state.base_features.get("neighbor_weighted_stringency_mean", 0.0))
    feature_values.setdefault("neighbor_count", state.base_features.get("neighbor_count", 0.0))

    feature_values["day_of_week"] = float(feature_date.weekday())
    feature_values["month"] = float(feature_date.month)

    vector: list[float] = []
    for column_name in feature_columns:
        if column_name.startswith("code_"):
            country_code = column_name[5:]
            vector.append(1.0 if country_code == state.code else 0.0)
            continue

        vector.append(float(feature_values.get(column_name, 0.0)))

    return np.asarray(vector, dtype=np.float32)
