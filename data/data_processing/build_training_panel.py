from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]
RAW_FILE = ROOT_DIR / "data" / "raw_data" / "compact.csv"
OUTPUT_FILE = ROOT_DIR / "data" / "processed_data" / "cleaned_panel_country_day.csv"
FEATURE_DICT_FILE = ROOT_DIR / "data" / "processed_data" / "feature_dictionary.txt"
SPLIT_DESC_FILE = ROOT_DIR / "data" / "processed_data" / "split_description.txt"


def load_base_frame() -> pd.DataFrame:
    usecols = [
        "country",
        "code",
        "date",
        "continent",
        "population",
        "population_density",
        "median_age",
        "life_expectancy",
        "gdp_per_capita",
        "hospital_beds_per_thousand",
        "human_development_index",
        "stringency_index",
        "reproduction_rate",
        "positive_rate",
        "total_tests",
        "new_tests",
        "total_vaccinations",
        "people_vaccinated",
        "people_fully_vaccinated",
        "total_boosters",
        "new_vaccinations",
        "new_cases",
        "new_deaths",
    ]

    df = pd.read_csv(RAW_FILE, usecols=usecols)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["code"] = df["code"].astype(str).str.upper().str.strip()

    # Keep only valid ISO-3 countries for country-day panel learning.
    df = df[df["code"].str.len() == 3].copy()
    df = df.dropna(subset=["date", "country"]).copy()

    # Avoid duplicate country-date records.
    df = df.sort_values(["code", "date"]).drop_duplicates(subset=["code", "date"], keep="last")

    return df


def add_cross_country_features(df: pd.DataFrame) -> pd.DataFrame:
    # Cross-country features are built ONLY from this project dataset.
    # No external border/entry-exit datasets are used.
    group_cols = ["date", "continent"]

    # Feature 1: same-continent peer 7-day mean new cases (excluding self).
    peer_group_roll7 = df.groupby(group_cols, sort=False)["new_cases_roll_mean_7"]
    roll7_sum = peer_group_roll7.transform("sum")
    roll7_cnt = peer_group_roll7.transform("count")
    df["region_peer_new_cases_roll7_mean"] = np.where(
        roll7_cnt > 1,
        (roll7_sum - df["new_cases_roll_mean_7"]) / (roll7_cnt - 1),
        df["new_cases_roll_mean_7"],
    )

    # Feature 2/3 proxies (same-continent peers excluding self).
    # Keep column names for downstream compatibility, while explicitly avoiding external border data.
    peer_group_cases = df.groupby(group_cols, sort=False)["new_cases"]
    peer_cases_sum = peer_group_cases.transform("sum")
    peer_cases_cnt = peer_group_cases.transform("count")
    df["neighbor_weighted_new_cases_mean"] = np.where(
        peer_cases_cnt > 1,
        (peer_cases_sum - df["new_cases"]) / (peer_cases_cnt - 1),
        0.0,
    )

    peer_group_stringency = df.groupby(group_cols, sort=False)["stringency_index"]
    peer_stringency_sum = peer_group_stringency.transform("sum")
    peer_stringency_cnt = peer_group_stringency.transform("count")
    df["neighbor_weighted_stringency_mean"] = np.where(
        peer_stringency_cnt > 1,
        (peer_stringency_sum - df["stringency_index"]) / (peer_stringency_cnt - 1),
        0.0,
    )

    df["neighbor_count"] = np.where(peer_cases_cnt > 1, peer_cases_cnt - 1, 0).astype(int)

    return df


def clean_features(df: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = [
        "population",
        "population_density",
        "median_age",
        "life_expectancy",
        "gdp_per_capita",
        "hospital_beds_per_thousand",
        "human_development_index",
        "stringency_index",
        "reproduction_rate",
        "positive_rate",
        "total_tests",
        "new_tests",
        "total_vaccinations",
        "people_vaccinated",
        "people_fully_vaccinated",
        "total_boosters",
        "new_vaccinations",
        "new_cases",
        "new_deaths",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values(["code", "date"]).reset_index(drop=True)
    by_country = df.groupby("code", sort=False)

    static_cols = [
        "population",
        "population_density",
        "median_age",
        "life_expectancy",
        "gdp_per_capita",
        "hospital_beds_per_thousand",
        "human_development_index",
    ]

    for col in static_cols:
        df[f"{col}_missing_flag"] = df[col].isna().astype(int)

    for col in static_cols:
        df[col] = by_country[col].transform(lambda s: s.ffill().bfill())

    # Fall back to global median (or 0 if entirely missing) to avoid NaNs in training matrix.
    for col in static_cols:
        if df[col].notna().any():
            median_value = df[col].median(skipna=True)
        else:
            median_value = 0
        df[col] = df[col].fillna(median_value)

    flow_cols = ["new_cases", "new_deaths", "new_tests", "new_vaccinations"]
    for col in flow_cols:
        df[col] = df[col].fillna(0)
        df[col] = df[col].clip(lower=0)

    cumulative_cols = [
        "total_tests",
        "total_vaccinations",
        "people_vaccinated",
        "people_fully_vaccinated",
        "total_boosters",
    ]
    for col in cumulative_cols:
        df[col] = by_country[col].transform(lambda s: s.ffill().fillna(0).cummax())

    df["stringency_index"] = by_country["stringency_index"].transform(lambda s: s.ffill()).fillna(0).clip(0, 100)
    df["reproduction_rate"] = by_country["reproduction_rate"].transform(lambda s: s.ffill()).fillna(0).clip(0, 10)
    df["positive_rate"] = by_country["positive_rate"].transform(lambda s: s.ffill()).fillna(0).clip(0, 1)

    # Fill remaining gaps in categorical columns.
    df["continent"] = df["continent"].fillna("Unknown")

    return df


def build_training_columns(df: pd.DataFrame) -> pd.DataFrame:
    by_country = df.groupby("code", sort=False)

    for lag in [1, 3, 7, 14]:
        df[f"new_cases_lag_{lag}"] = by_country["new_cases"].shift(lag)
        df[f"new_deaths_lag_{lag}"] = by_country["new_deaths"].shift(lag)

    df["new_cases_roll_mean_7"] = by_country["new_cases"].transform(lambda s: s.rolling(7, min_periods=1).mean())
    df["new_cases_roll_mean_14"] = by_country["new_cases"].transform(lambda s: s.rolling(14, min_periods=1).mean())
    df["new_cases_growth_1d"] = by_country["new_cases"].pct_change(1)
    df["new_cases_growth_7d"] = by_country["new_cases"].pct_change(7)

    df = add_cross_country_features(df)

    df["day_of_week"] = df["date"].dt.dayofweek
    df["month"] = df["date"].dt.month

    # Supervised label: next-day new cases.
    df["target_next_day_new_cases"] = by_country["new_cases"].shift(-1)

    lag_and_growth_cols = [
        c for c in df.columns if c.startswith("new_cases_lag_") or c.startswith("new_deaths_lag_")
    ] + ["new_cases_growth_1d", "new_cases_growth_7d"]

    df[lag_and_growth_cols] = df[lag_and_growth_cols].replace([np.inf, -np.inf], np.nan).fillna(0)

    df = df.dropna(subset=["target_next_day_new_cases"]).copy()
    df["target_next_day_new_cases"] = df["target_next_day_new_cases"].clip(lower=0)

    return df


def add_time_splits(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    unique_dates = pd.Series(sorted(df["date"].unique()))
    train_end = unique_dates.iloc[int(len(unique_dates) * 0.70)]
    val_end = unique_dates.iloc[int(len(unique_dates) * 0.85)]

    df["data_split"] = np.where(
        df["date"] <= train_end,
        "train",
        np.where(df["date"] <= val_end, "validation", "test"),
    )

    return df, pd.Timestamp(train_end), pd.Timestamp(val_end)


def write_feature_dictionary() -> None:
    text = """Feature Dictionary (cleaned_panel_country_day.csv)

Primary Keys:
- code: ISO-3 country code
- date: observation date (daily)

Label:
- target_next_day_new_cases: supervised target, next-day new cases for each country

Core Epidemiology Features:
- new_cases, new_deaths
- new_cases_lag_1, new_cases_lag_3, new_cases_lag_7, new_cases_lag_14
- new_deaths_lag_1, new_deaths_lag_3, new_deaths_lag_7, new_deaths_lag_14
- new_cases_roll_mean_7, new_cases_roll_mean_14
- new_cases_growth_1d, new_cases_growth_7d

Policy and Transmission Features:
- stringency_index: policy stringency (0-100)
- reproduction_rate
- positive_rate

Vaccination Features:
- total_vaccinations
- people_vaccinated
- people_fully_vaccinated
- total_boosters
- new_vaccinations

Testing Features:
- total_tests
- new_tests

Static Country Features:
- continent
- population
- population_density
- median_age
- life_expectancy
- gdp_per_capita
- hospital_beds_per_thousand
- human_development_index

Missingness Flags (for static features):
- population_missing_flag
- population_density_missing_flag
- median_age_missing_flag
- life_expectancy_missing_flag
- gdp_per_capita_missing_flag
- hospital_beds_per_thousand_missing_flag
- human_development_index_missing_flag

Calendar Features:
- day_of_week
- month

Cross-Country Transmission Features (V3):
- region_peer_new_cases_roll7_mean: same-continent peer mean of 7-day new-cases trend (excluding self)
- neighbor_weighted_new_cases_mean: same-continent peer mean of same-day new cases (external border data not used)
- neighbor_weighted_stringency_mean: same-continent peer mean of same-day stringency index (external border data not used)
- neighbor_count: number of same-continent peer countries (excluding self)

Data Split:
- data_split: train / validation / test (time-based split)
"""
    FEATURE_DICT_FILE.write_text(text, encoding="utf-8")


def write_split_description(train_end: pd.Timestamp, val_end: pd.Timestamp, max_date: pd.Timestamp) -> None:
    text = f"""Time-Based Split Description

Split strategy:
- Strict chronological split (no random shuffle)
- Train: date <= {train_end.date()}
- Validation: {train_end.date()} < date <= {val_end.date()}
- Test: {val_end.date()} < date <= {max_date.date()}

Reason:
- Avoid temporal leakage
- Simulate real next-day forecasting in production
"""
    SPLIT_DESC_FILE.write_text(text, encoding="utf-8")


def main() -> None:
    df = load_base_frame()
    df = clean_features(df)
    df = build_training_columns(df)
    df, train_end, val_end = add_time_splits(df)

    df = df.sort_values(["code", "date"]).reset_index(drop=True)
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    write_feature_dictionary()
    max_date = pd.to_datetime(df["date"]).max()
    write_split_description(train_end, val_end, max_date)

    print(f"Saved: {OUTPUT_FILE}")
    print(f"Rows: {len(df):,}")
    print(f"Countries: {df['code'].nunique():,}")
    print(f"Date range: {df['date'].min()} -> {df['date'].max()}")
    print(df["data_split"].value_counts().to_string())


if __name__ == "__main__":
    main()
