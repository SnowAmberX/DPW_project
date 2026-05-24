from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_PATH = ROOT / "public" / "overview" / "country_quarterly_overview.csv"


def quarter_key(date_value: str) -> str:
    year = int(date_value[0:4])
    month = int(date_value[5:7])
    quarter = ((month - 1) // 3) + 1
    return f"{year}Q{quarter}"


def to_float(value: str) -> float | None:
    try:
      numeric = float(value)
    except (TypeError, ValueError):
      return None
    return numeric


def build_vaccination_metrics() -> dict[tuple[str, str], dict[str, float | str]]:
    rows: dict[tuple[str, str], dict[str, float | str]] = {}
    buckets: dict[tuple[str, str], dict[str, object]] = defaultdict(
        lambda: {
            "country": "",
            "quarter": "",
            "speed_values": [],
            "latest_date": "",
            "rolling_6m": None,
            "rolling_12m": None,
        }
    )

    with (DATA_DIR / "cleaned_vaccinations_global.txt").open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            country = (row.get("country") or "").strip()
            date_value = (row.get("date") or "").strip()
            if not country or not date_value:
                continue

            key = (country, quarter_key(date_value))
            bucket = buckets[key]
            bucket["country"] = country
            bucket["quarter"] = key[1]

            speed = to_float(row.get("daily_people_vaccinated_smoothed_per_hundred", ""))
            if speed is not None:
                bucket["speed_values"].append(speed)

            latest_date = bucket["latest_date"]
            if not latest_date or date_value >= latest_date:
                bucket["latest_date"] = date_value
                bucket["rolling_6m"] = to_float(row.get("rolling_vaccinations_6m_per_hundred", ""))
                bucket["rolling_12m"] = to_float(row.get("rolling_vaccinations_12m_per_hundred", ""))

    for key, bucket in buckets.items():
        speed_values = [value for value in bucket["speed_values"] if value is not None]
        rows[key] = {
            "country": bucket["country"],
            "quarter": bucket["quarter"],
            "vacc_rollout_speed_avg": sum(speed_values) / len(speed_values) if speed_values else "",
            "vacc_rolling_6m_per_hundred": bucket["rolling_6m"] if bucket["rolling_6m"] is not None else "",
            "vacc_rolling_12m_per_hundred": bucket["rolling_12m"] if bucket["rolling_12m"] is not None else "",
        }

    return rows


def build_case_metrics() -> dict[tuple[str, str], dict[str, float | str]]:
    rows: dict[tuple[str, str], dict[str, float | str]] = {}
    buckets: dict[tuple[str, str], dict[str, object]] = defaultdict(
        lambda: {
            "country": "",
            "quarter": "",
            "new_cases_pm_values": [],
            "new_cases_pm7_values": [],
            "latest_date": "",
            "total_cases_pm": None,
        }
    )

    with (DATA_DIR / "cleaned_cases_deaths.txt").open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            country = (row.get("country") or "").strip()
            date_value = (row.get("date") or "").strip()
            if not country or not date_value:
                continue

            key = (country, quarter_key(date_value))
            bucket = buckets[key]
            bucket["country"] = country
            bucket["quarter"] = key[1]

            cases_pm = to_float(row.get("new_cases_per_million", ""))
            if cases_pm is not None:
                bucket["new_cases_pm_values"].append(cases_pm)

            cases_pm7 = to_float(row.get("new_cases_per_million_7_day_avg_right", ""))
            if cases_pm7 is not None:
                bucket["new_cases_pm7_values"].append(cases_pm7)

            latest_date = bucket["latest_date"]
            if not latest_date or date_value >= latest_date:
                bucket["latest_date"] = date_value
                bucket["total_cases_pm"] = to_float(row.get("total_cases_per_million", ""))

    for key, bucket in buckets.items():
        cases_pm_values = [value for value in bucket["new_cases_pm_values"] if value is not None]
        cases_pm7_values = [value for value in bucket["new_cases_pm7_values"] if value is not None]
        rows[key] = {
            "country": bucket["country"],
            "quarter": bucket["quarter"],
            "cases_new_cases_pm_avg": sum(cases_pm_values) / len(cases_pm_values) if cases_pm_values else "",
            "cases_new_cases_pm7_avg": sum(cases_pm7_values) / len(cases_pm7_values) if cases_pm7_values else "",
            "cases_total_cases_pm_latest": bucket["total_cases_pm"] if bucket["total_cases_pm"] is not None else "",
        }

    return rows


def main() -> None:
    vaccination_rows = build_vaccination_metrics()
    case_rows = build_case_metrics()
    all_keys = sorted(set(vaccination_rows) | set(case_rows), key=lambda item: (item[1], item[0]))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "country",
                "quarter",
                "vacc_rollout_speed_avg",
                "vacc_rolling_6m_per_hundred",
                "vacc_rolling_12m_per_hundred",
                "cases_new_cases_pm_avg",
                "cases_new_cases_pm7_avg",
                "cases_total_cases_pm_latest",
            ],
        )
        writer.writeheader()
        for key in all_keys:
            writer.writerow(
                {
                    "country": key[0],
                    "quarter": key[1],
                    **vaccination_rows.get(key, {}),
                    **case_rows.get(key, {}),
                }
            )

    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
