from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from functools import lru_cache
import os

import numpy as np

from app.services.traditional_onnx.traditional_onnx_feature_builder import (
    build_traditional_onnx_dynamic_feature_context,
    build_traditional_onnx_feature_vector,
    create_traditional_onnx_runtime_states,
)
from app.services.traditional_onnx.traditional_onnx_repository import (
    TraditionalOnnxModelSpec,
    TraditionalOnnxRuntimeBundle,
    load_traditional_onnx_runtime_bundle,
)
from app.services.traditional_onnx.traditional_onnx_utils import (
    normalize_traditional_country_key,
    parse_traditional_date,
)

try:
    import onnxruntime as ort
except Exception:  # pragma: no cover - handled at runtime via error response.
    ort = None


DEFAULT_TRADITIONAL_ONNX_MAX_WORKERS = 8
DEFAULT_TRADITIONAL_ONNX_INTRA_OP_THREADS = 1
DEFAULT_TRADITIONAL_ONNX_INTER_OP_THREADS = 1


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default

    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


ACTIVE_CASES_RECOVERY_DAYS = 21.0


@lru_cache(maxsize=1)
def _get_traditional_prediction_pool() -> ThreadPoolExecutor:
    cpu_count = os.cpu_count() or 4
    configured_max_workers = os.getenv("TRADITIONAL_ONNX_MAX_WORKERS")

    if configured_max_workers and configured_max_workers.isdigit():
        max_workers = max(1, int(configured_max_workers))
    else:
        max_workers = max(1, min(DEFAULT_TRADITIONAL_ONNX_MAX_WORKERS, cpu_count))

    return ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="traditional-onnx")


@lru_cache(maxsize=128)
def _get_traditional_onnx_session(onnx_model_path: str):
    if ort is None:
        raise RuntimeError("onnxruntime is not installed in backend environment.")

    session_options = ort.SessionOptions()

    configured_intra_threads = os.getenv("TRADITIONAL_ONNX_INTRA_OP_THREADS")
    configured_inter_threads = os.getenv("TRADITIONAL_ONNX_INTER_OP_THREADS")

    session_options.intra_op_num_threads = (
        int(configured_intra_threads)
        if configured_intra_threads and configured_intra_threads.isdigit()
        else DEFAULT_TRADITIONAL_ONNX_INTRA_OP_THREADS
    )
    session_options.inter_op_num_threads = (
        int(configured_inter_threads)
        if configured_inter_threads and configured_inter_threads.isdigit()
        else DEFAULT_TRADITIONAL_ONNX_INTER_OP_THREADS
    )
    session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

    session = ort.InferenceSession(
        onnx_model_path,
        sess_options=session_options,
        providers=["CPUExecutionProvider"],
    )
    input_name = session.get_inputs()[0].name
    return session, input_name


def _extract_traditional_onnx_scalar(outputs: list[object]) -> float:
    for output in outputs:
        array = np.asarray(output)
        if array.size == 0:
            continue
        if np.issubdtype(array.dtype, np.number):
            return float(array.reshape(-1)[0])
    raise RuntimeError("Traditional ONNX model output does not contain numeric tensor.")


def _predict_traditional_onnx_next_day_active_change(model_spec: TraditionalOnnxModelSpec, feature_vector: np.ndarray) -> float:
    if feature_vector.ndim != 1:
        raise ValueError("Traditional ONNX feature vector must be 1-D.")

    session, input_name = _get_traditional_onnx_session(str(model_spec.onnx_model_path))
    outputs = session.run(None, {input_name: feature_vector.reshape(1, -1).astype(np.float32)})
    prediction_change = _extract_traditional_onnx_scalar(outputs)
    if not np.isfinite(prediction_change):
        return 0.0
    return float(prediction_change)


def _estimate_traditional_initial_active_cases(state) -> float:
    # Approximate current active cases by recent incidence minus deaths over infectious window.
    recent_cases = list(state.new_cases_history)[-int(ACTIVE_CASES_RECOVERY_DAYS):]
    recent_deaths = list(state.new_deaths_history)[-int(ACTIVE_CASES_RECOVERY_DAYS):]
    if not recent_cases:
        return 0.0
    return max(float(sum(recent_cases) - sum(recent_deaths)), 0.0)


def _resolve_traditional_onnx_origin_country_code(bundle: TraditionalOnnxRuntimeBundle, origin_country: str) -> str:
    candidate = str(origin_country).strip()
    if not candidate:
        raise ValueError("origin_country is required.")

    upper_candidate = candidate.upper()
    if len(upper_candidate) == 3 and upper_candidate in bundle.country_seeds_by_code:
        return upper_candidate

    country_key = normalize_traditional_country_key(candidate)
    resolved = bundle.country_code_by_normalized_name.get(country_key)
    if resolved:
        return resolved

    raise ValueError(f"Unsupported origin_country: {origin_country}")


def _calculate_traditional_delay_days(origin_first_case, country_first_case) -> int:
    if origin_first_case is None or country_first_case is None:
        return 0
    delta = (country_first_case - origin_first_case).days
    return max(delta, 0)


def _select_traditional_onnx_model_spec(bundle: TraditionalOnnxRuntimeBundle, code: str) -> TraditionalOnnxModelSpec:
    # Fast mode for interactive UX: avoid loading/running 200+ country-specific ONNX sessions
    # on every request. Set TRADITIONAL_ONNX_USE_GLOBAL_FALLBACK_ONLY=0 to restore per-country models.
    if _env_flag("TRADITIONAL_ONNX_USE_GLOBAL_FALLBACK_ONLY", True):
        return bundle.global_fallback_spec

    spec = bundle.model_specs_by_code.get(code)
    if spec is None:
        return bundle.global_fallback_spec
    return spec


def forecast_traditional_onnx_global_infections(
    origin_country: str,
    forecast_days: int,
    start_date: str | None,
    step_days: int,
) -> dict:
    if forecast_days < 1:
        raise ValueError("forecast_days must be greater than or equal to 1.")
    if step_days < 1:
        raise ValueError("step_days must be greater than or equal to 1.")

    bundle = load_traditional_onnx_runtime_bundle()
    if not bundle.country_seeds_by_code:
        raise ValueError("No country seed data loaded for traditional ONNX forecasting.")

    origin_code = _resolve_traditional_onnx_origin_country_code(bundle, origin_country)
    origin_seed = bundle.country_seeds_by_code[origin_code]

    simulation_start_date = (
        parse_traditional_date(start_date, field_name="start_date")
        if start_date
        else bundle.latest_observation_date
    )

    states_by_code = create_traditional_onnx_runtime_states(bundle.country_seeds_by_code)
    active_cases_by_code: dict[str, float] = {
        code: _estimate_traditional_initial_active_cases(state)
        for code, state in states_by_code.items()
    }
    frames: list[dict] = []
    max_infections = 0
    prediction_pool = _get_traditional_prediction_pool()

    for day_index in range(1, forecast_days + 1):
        forecast_date = simulation_start_date + timedelta(days=day_index)
        dynamic_context = build_traditional_onnx_dynamic_feature_context(states_by_code)

        predicted_active_change_by_code: dict[str, float] = {}

        def _predict_one_country(item: tuple[str, object]) -> tuple[str, float]:
            code, state = item
            model_spec = _select_traditional_onnx_model_spec(bundle, code)
            delay_days = _calculate_traditional_delay_days(origin_seed.first_case_date, state.first_case_date)

            if day_index <= delay_days:
                return code, 0.0

            feature_vector = build_traditional_onnx_feature_vector(
                state=state,
                feature_columns=model_spec.feature_columns,
                feature_date=forecast_date,
                dynamic_context=dynamic_context,
            )
            prediction_change = _predict_traditional_onnx_next_day_active_change(model_spec, feature_vector)
            return code, prediction_change

        for code, prediction_change in prediction_pool.map(_predict_one_country, states_by_code.items()):
            predicted_active_change_by_code[code] = prediction_change

        for code, predicted_change in predicted_active_change_by_code.items():
            state = states_by_code[code]
            latest_cases = float(state.new_cases_history[-1]) if state.new_cases_history else 0.0
            active_cases = float(active_cases_by_code.get(code, 0.0))

            next_active_cases = max(active_cases + predicted_change, 0.0)
            active_cases_by_code[code] = next_active_cases

            # Keep recursive features moving without introducing transmission simulation.
            pseudo_new_cases = max(latest_cases + predicted_change, 0.0)
            state.new_cases_history.append(pseudo_new_cases)
            state.new_deaths_history.append(0.0)

        if day_index % step_days != 0 and day_index != forecast_days:
            continue

        infections_by_country: dict[str, int] = {}
        for code, active_cases in active_cases_by_code.items():
            country_name = states_by_code[code].country_name
            rounded_cases = int(max(0.0, np.floor(active_cases)))
            infections_by_country[country_name] = rounded_cases
            if rounded_cases > max_infections:
                max_infections = rounded_cases

        frames.append(
            {
                "date": forecast_date.isoformat(),
                "infections_by_country": infections_by_country,
            }
        )

    if not frames:
        raise ValueError("Traditional ONNX forecasting produced no frames.")

    return {
        "model_family": "traditional_onnx",
        "metric": "predicted_active_cases",
        "origin_country_code": origin_code,
        "origin_country_name": origin_seed.country_name,
        "origin_first_case_date": origin_seed.first_case_date.isoformat() if origin_seed.first_case_date else None,
        "frame_count": len(frames),
        "forecast_days": forecast_days,
        "step_days": step_days,
        "start_date": frames[0]["date"],
        "end_date": frames[-1]["date"],
        "max_infections": max_infections,
        "frames": frames,
    }
