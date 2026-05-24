import pandas as pd
import numpy as np

# =========================
# Part 2. Data analysis
# After merging country-type attributes
# =========================

# Define representative region-level and income-level aggregate groups
aggregate_groups = [
    "World",
    "Africa",
    "Asia",
    "Europe",
    "North America",
    "South America",
    "Oceania",
    "European Union (27)",
    "High-income countries",
    "Upper-middle-income countries",
    "Lower-middle-income countries",
    "Low-income countries"
]

# Keep only aggregate groups for coverage and rollout comparison
df_group_coverage = df_coverage_clean[
    df_coverage_clean["country"].isin(aggregate_groups)
].copy()

df_group_coverage["quarter"] = df_group_coverage["date"].dt.to_period("Q").astype(str)

# Compute final cumulative values for progress-ratio calculation
group_final_values = (
    df_group_coverage.groupby("country")
    .agg(
        final_people_vaccinated=("people_vaccinated_interpolated", "max"),
        final_people_fully_vaccinated=("people_fully_vaccinated_interpolated", "max")
    )
    .reset_index()
)

df_group_coverage = df_group_coverage.merge(group_final_values, on="country", how="left")

# Compute normalized rollout progress ratios
df_group_coverage["vaccinated_progress_ratio"] = (
    df_group_coverage["people_vaccinated_interpolated"] /
    df_group_coverage["final_people_vaccinated"]
)

df_group_coverage["fully_vaccinated_progress_ratio"] = (
    df_group_coverage["people_fully_vaccinated_interpolated"] /
    df_group_coverage["final_people_fully_vaccinated"]
)

# Aggregate quarterly rollout indicators
group_quarterly = (
    df_group_coverage.groupby(["country", "quarter"])
    .agg(
        rollout_speed=("daily_people_vaccinated_smoothed_per_hundred", "mean"),
        first_dose_progress=("vaccinated_progress_ratio", "mean"),
        full_vaccination_progress=("fully_vaccinated_progress_ratio", "mean")
    )
    .reset_index()
)

# Build group-type metadata
group_meta = pd.DataFrame([
    {"country": "Africa", "group_type": "region", "display_order": 1},
    {"country": "Asia", "group_type": "region", "display_order": 2},
    {"country": "Europe", "group_type": "region", "display_order": 3},
    {"country": "North America", "group_type": "region", "display_order": 4},
    {"country": "South America", "group_type": "region", "display_order": 5},
    {"country": "Oceania", "group_type": "region", "display_order": 6},
    {"country": "European Union (27)", "group_type": "region_special", "display_order": 7},
    {"country": "High-income countries", "group_type": "income", "display_order": 8},
    {"country": "Upper-middle-income countries", "group_type": "income", "display_order": 9},
    {"country": "Lower-middle-income countries", "group_type": "income", "display_order": 10},
    {"country": "Low-income countries", "group_type": "income", "display_order": 11},
    {"country": "World", "group_type": "global", "display_order": 12},
])

# Merge group metadata into the quarterly summary table
group_quarterly = group_quarterly.merge(group_meta, on="country", how="left")

# Export core quarterly tables
group_meta.to_csv("group_meta.csv", index=False)
group_quarterly.to_csv("group_quarterly_rollout_enriched.csv", index=False)

# Convert to long format for flexible plotting
group_quarterly_long = group_quarterly.melt(
    id_vars=["country", "quarter", "group_type", "display_order"],
    value_vars=["rollout_speed", "first_dose_progress", "full_vaccination_progress"],
    var_name="metric",
    value_name="value"
)

group_quarterly_long = group_quarterly_long.sort_values(
    ["group_type", "display_order", "quarter", "metric"]
).reset_index(drop=True)

group_quarterly_long.to_csv("group_quarterly_long.csv", index=False)

# Rank groups within each quarter for each metric
ranking_rows = []

for metric in ["rollout_speed", "first_dose_progress", "full_vaccination_progress"]:
    temp = group_quarterly[["country", "quarter", "group_type", "display_order", metric]].copy()
    temp = temp.rename(columns={metric: "value"})
    temp["rank_within_quarter"] = temp.groupby("quarter")["value"].rank(
        method="min", ascending=False
    )
    temp["metric"] = metric
    ranking_rows.append(temp)

group_rankings_by_quarter = pd.concat(ranking_rows, ignore_index=True)
group_rankings_by_quarter = group_rankings_by_quarter.sort_values(
    ["metric", "quarter", "rank_within_quarter", "display_order"]
).reset_index(drop=True)

group_rankings_by_quarter.to_csv("group_rankings_by_quarter.csv", index=False)

# Compute quarter-over-quarter changes
group_qoq_change = group_quarterly.sort_values(["country", "quarter"]).copy()

for metric in ["rollout_speed", "first_dose_progress", "full_vaccination_progress"]:
    group_qoq_change[f"{metric}_qoq_change"] = group_qoq_change.groupby("country")[metric].diff()

# Identify the quarter with the largest positive change for each group and metric
peak_change_rows = []

for country, temp in group_qoq_change.groupby("country"):
    for metric in ["rollout_speed", "first_dose_progress", "full_vaccination_progress"]:
        col = f"{metric}_qoq_change"
        temp2 = temp.dropna(subset=[col]).sort_values(col, ascending=False)

        if len(temp2) == 0:
            continue

        best = temp2.iloc[0]

        peak_change_rows.append({
            "country": country,
            "metric": metric,
            "peak_change_quarter": best["quarter"],
            "peak_qoq_change": best[col]
        })

group_peak_change_summary = pd.DataFrame(peak_change_rows)

group_qoq_change.to_csv("group_qoq_change.csv", index=False)
group_peak_change_summary.to_csv("group_peak_change_summary.csv", index=False)

# Build milestone table for key progress thresholds
milestone_thresholds = [0.25, 0.50, 0.75]
milestone_rows = []

for country, temp in group_quarterly.groupby("country"):
    temp = temp.sort_values("quarter")

    for metric in ["first_dose_progress", "full_vaccination_progress"]:
        for threshold in milestone_thresholds:
            reached = temp[temp[metric] >= threshold]

            milestone_rows.append({
                "country": country,
                "metric": metric,
                "threshold": threshold,
                "first_quarter_reached": reached.iloc[0]["quarter"] if len(reached) > 0 else np.nan
            })

group_milestone_table = pd.DataFrame(milestone_rows)
group_milestone_table.to_csv("group_milestone_table.csv", index=False)

# Build summary cards for dashboard overview
group_overview_cards = (
    group_quarterly.groupby("country")
    .agg(
        latest_quarter=("quarter", "max"),
        peak_rollout_speed=("rollout_speed", "max"),
        avg_rollout_speed=("rollout_speed", "mean"),
        max_first_dose_progress=("first_dose_progress", "max"),
        max_full_vaccination_progress=("full_vaccination_progress", "max")
    )
    .reset_index()
)

group_overview_cards = group_overview_cards.merge(group_meta, on="country", how="left")

for col in [
    "peak_rollout_speed",
    "avg_rollout_speed",
    "max_first_dose_progress",
    "max_full_vaccination_progress"
]:
    group_overview_cards[col] = group_overview_cards[col].round(4)

group_overview_cards.to_csv("group_overview_cards.csv", index=False)

# Split into region/global and income-group tables
region_quarterly = group_quarterly[
    group_quarterly["group_type"].isin(["region", "region_special", "global"])
].copy()

income_quarterly = group_quarterly[
    group_quarterly["group_type"] == "income"
].copy()

region_quarterly.to_csv("region_quarterly_rollout.csv", index=False)
income_quarterly.to_csv("income_quarterly_rollout.csv", index=False)

# Build a compact summary table for each group
group_summary = (
    group_quarterly.groupby("country")
    .agg(
        peak_rollout_speed=("rollout_speed", "max"),
        avg_rollout_speed=("rollout_speed", "mean"),
        final_first_dose_progress=("first_dose_progress", "max"),
        final_full_vaccination_progress=("full_vaccination_progress", "max")
    )
    .reset_index()
)

peak_quarter_rows = []

for country, temp in group_quarterly.groupby("country"):
    temp = temp.sort_values("rollout_speed", ascending=False)
    best = temp.iloc[0]

    peak_quarter_rows.append({
        "country": country,
        "peak_rollout_quarter": best["quarter"],
        "peak_rollout_speed": best["rollout_speed"]
    })

peak_quarter_df = pd.DataFrame(peak_quarter_rows)

group_summary = group_summary.merge(
    peak_quarter_df, on=["country", "peak_rollout_speed"], how="left"
)
group_summary = group_summary.merge(group_meta, on="country", how="left")

group_summary.to_csv("group_summary.csv", index=False)