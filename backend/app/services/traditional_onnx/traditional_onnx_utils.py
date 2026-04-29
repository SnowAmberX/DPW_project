from __future__ import annotations

from datetime import date, datetime


def normalize_traditional_country_key(value: str) -> str:
    return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())


def parse_traditional_date(value: str, field_name: str = "date") -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format.") from exc


def safe_traditional_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    try:
        numeric = float(text)
    except ValueError:
        return default
    if numeric != numeric:
        return default
    return numeric
