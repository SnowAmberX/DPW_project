import csv
from collections import defaultdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path

DATE_FORMAT = "%Y-%m-%d"
DATA_FILE = Path(__file__).resolve().parents[3] / "data" / "processed_data" / "cleaned_cases_deaths.csv"


def _to_non_negative_int(value: str | None) -> int:
    if value is None or value == "":
        return 0

    try:
        numeric_value = float(value)
    except ValueError:
        return 0

    return max(int(numeric_value), 0)


def _validate_date_string(value: str, field_name: str) -> str:
    try:
        datetime.strptime(value, DATE_FORMAT)
    except ValueError as exc:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format.") from exc

    return value


@lru_cache(maxsize=1)
def _load_cases_grouped_by_date() -> tuple[list[str], dict[str, dict[str, int]]]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Timeline data file not found: {DATA_FILE}")

    grouped_cases: defaultdict[str, dict[str, int]] = defaultdict(dict)

    with DATA_FILE.open("r", encoding="utf-8", newline="") as source_file:
        reader = csv.DictReader(source_file)
        expected_columns = {"country", "date", "total_cases"}

        if reader.fieldnames is None or not expected_columns.issubset(set(reader.fieldnames)):
            raise ValueError("Timeline data file is missing required columns: country, date, total_cases")

        for row in reader:
            date_value = (row.get("date") or "").strip()
            country_name = (row.get("country") or "").strip()

            if not date_value or not country_name:
                continue

            grouped_cases[date_value][country_name] = _to_non_negative_int(row.get("total_cases"))

    ordered_dates = sorted(grouped_cases.keys())
    ordered_payload = {date_key: grouped_cases[date_key] for date_key in ordered_dates}

    return ordered_dates, ordered_payload


def build_infection_timeline(start_date: str | None, end_date: str | None, step_days: int) -> dict:
    if step_days < 1:
        raise ValueError("step_days must be greater than or equal to 1.")

    normalized_start = _validate_date_string(start_date, "start_date") if start_date else None
    normalized_end = _validate_date_string(end_date, "end_date") if end_date else None

    if normalized_start and normalized_end and normalized_start > normalized_end:
        raise ValueError("start_date cannot be later than end_date.")

    ordered_dates, grouped_cases = _load_cases_grouped_by_date()

    selected_dates = [
        date_key
        for date_key in ordered_dates
        if (normalized_start is None or date_key >= normalized_start)
        and (normalized_end is None or date_key <= normalized_end)
    ]

    if not selected_dates:
        raise ValueError("No timeline data found for the selected date range.")

    sampled_dates = selected_dates[::step_days]
    if sampled_dates[-1] != selected_dates[-1]:
        sampled_dates.append(selected_dates[-1])

    frames = [
        {
            "date": date_key,
            "infections_by_country": dict(grouped_cases[date_key]),
        }
        for date_key in sampled_dates
    ]

    max_infections = 0
    for frame in frames:
        frame_max = max(frame["infections_by_country"].values(), default=0)
        max_infections = max(max_infections, frame_max)

    return {
        "metric": "total_cases",
        "frame_count": len(frames),
        "start_date": sampled_dates[0],
        "end_date": sampled_dates[-1],
        "max_infections": max_infections,
        "frames": frames,
    }
