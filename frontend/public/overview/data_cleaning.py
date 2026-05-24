import pandas as pd
import numpy as np

# =========================
# Part 1. Data cleaning
# Before merging country-type attributes
# =========================

# Read the global vaccination dataset
df = pd.read_csv("cleaned_vaccinations_global.csv")

# Convert the date column to datetime format
df["date"] = pd.to_datetime(df["date"])

# Keep only the fields required for rollout and coverage analysis
needed_cols = [
    "country",
    "date",
    "daily_vaccinations_smoothed",
    "daily_people_vaccinated_smoothed",
    "daily_people_vaccinated_smoothed_per_hundred",
    "people_vaccinated_interpolated",
    "people_fully_vaccinated_interpolated",
    "total_boosters_interpolated"
]
df = df[needed_cols].copy()

# Sort the dataset by country and date
df = df.sort_values(["country", "date"]).reset_index(drop=True)

# Build a quality table to evaluate whether each country's rollout records are suitable
quality_rows = []

for country, temp in df.groupby("country"):
    temp = temp.sort_values("date").copy()

    final_people_vaccinated = temp["people_vaccinated_interpolated"].max()
    final_people_fully_vaccinated = temp["people_fully_vaccinated_interpolated"].max()
    final_boosters = temp["total_boosters_interpolated"].max()

    temp["vacc_diff"] = temp["people_vaccinated_interpolated"].diff()

    first_nonzero_date = temp.loc[
        temp["people_vaccinated_interpolated"] > 0, "date"
    ].min()

    first_change_idx = temp.index[temp["vacc_diff"] > 0]

    if len(first_change_idx) > 0:
        first_change_idx = first_change_idx[0]
        first_change_date = temp.loc[first_change_idx, "date"]
        baseline_at_first_change = temp.loc[first_change_idx, "people_vaccinated_interpolated"]
    else:
        first_change_date = pd.NaT
        baseline_at_first_change = np.nan

    if pd.notna(final_people_vaccinated) and final_people_vaccinated > 0:
        baseline_ratio = baseline_at_first_change / final_people_vaccinated
    else:
        baseline_ratio = np.nan

    quality_rows.append({
        "country": country,
        "first_nonzero_date": first_nonzero_date,
        "first_change_date": first_change_date,
        "baseline_at_first_change": baseline_at_first_change,
        "final_people_vaccinated": final_people_vaccinated,
        "final_people_fully_vaccinated": final_people_fully_vaccinated,
        "final_boosters": final_boosters,
        "baseline_ratio": baseline_ratio
    })

country_quality_table = pd.DataFrame(quality_rows)

# Classify rollout recording quality based on the baseline ratio
def classify_rollout_quality(row):
    if pd.isna(row["baseline_ratio"]):
        return "bad_no_rollout_signal"
    elif row["baseline_ratio"] <= 0.02:
        return "good_for_rollout"
    elif row["baseline_ratio"] <= 0.10:
        return "usable_with_caution"
    else:
        return "late_start_recording"

country_quality_table["rollout_quality"] = country_quality_table.apply(
    classify_rollout_quality, axis=1
)

# Mark whether a country can be used for rollout-start analysis
country_quality_table["use_for_rollout_start_analysis"] = country_quality_table[
    "rollout_quality"
].isin(["good_for_rollout", "usable_with_caution"])

# Mark whether a country can be used for coverage analysis
country_quality_table["use_for_coverage_analysis"] = (
    country_quality_table["final_people_vaccinated"] > 0
)

# Save countries with problematic late-start recording
problem_countries = country_quality_table[
    country_quality_table["rollout_quality"] == "late_start_recording"
].sort_values("baseline_ratio", ascending=False)

# Keep only countries suitable for rollout-start analysis
rollout_ok_countries = country_quality_table.loc[
    country_quality_table["use_for_rollout_start_analysis"], "country"
].tolist()

df_rollout_clean = df[df["country"].isin(rollout_ok_countries)].copy()

# Keep only countries suitable for coverage analysis
coverage_ok_countries = country_quality_table.loc[
    country_quality_table["use_for_coverage_analysis"], "country"
].tolist()

df_coverage_clean = df[df["country"].isin(coverage_ok_countries)].copy()

# Align rollout trajectories by the first valid change date
aligned_rows = []

for country, temp in df_rollout_clean.groupby("country"):
    temp = temp.sort_values("date").copy()
    temp["vacc_diff"] = temp["people_vaccinated_interpolated"].diff()

    first_change_date = temp.loc[temp["vacc_diff"] > 0, "date"].min()

    if pd.isna(first_change_date):
        continue

    temp = temp[temp["date"] >= first_change_date].copy()
    temp["rollout_day"] = (temp["date"] - first_change_date).dt.days

    aligned_rows.append(temp)

aligned_rollout_df = pd.concat(aligned_rows, ignore_index=True)

# Add quarter labels for later group-level analysis
df_coverage_clean["quarter"] = df_coverage_clean["date"].dt.to_period("Q").astype(str)

# Export cleaned intermediate datasets
country_quality_table.to_csv("country_quality_table.csv", index=False)
problem_countries.to_csv("problem_countries_top30.csv", index=False)
df_rollout_clean.to_csv("df_rollout_clean.csv", index=False)
aligned_rollout_df.to_csv("aligned_rollout_df.csv", index=False)
df_coverage_clean.to_csv("df_coverage_clean.csv", index=False)