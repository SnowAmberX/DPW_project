from pathlib import Path
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

COUNTRIES = ["United States", "China", "India", "Japan"]

def _find_frontend_root() -> Path:
    current = Path(__file__).resolve().parent
    for candidate in [current, *current.parents]:
        if (candidate / "public").exists() and (candidate / "src").exists():
            return candidate
    raise RuntimeError("Unable to locate frontend root containing public/ and src/")


PROJECT_ROOT = _find_frontend_root()
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "public" / "cases-vaccination"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CASES_FILE = DATA_DIR / "cleaned_cases_deaths.txt"
VACCINE_FILE = DATA_DIR / "cleaned_vaccinations_global.txt"
COMPACT_FILE = DATA_DIR / "cleaned_compact.txt"

if not CASES_FILE.exists():
    CASES_FILE = DATA_DIR / "cleaned_cases_deaths.csv"
if not VACCINE_FILE.exists():
    VACCINE_FILE = DATA_DIR / "cleaned_vaccinations_global.csv"
if not COMPACT_FILE.exists():
    COMPACT_FILE = DATA_DIR / "cleaned_compact.csv"

CHUNKSIZE = 300_000
ANALYSIS_START_DATE = pd.Timestamp("2020-01-01")
ANALYSIS_END_DATE = pd.Timestamp("2023-12-31")
DATE_AXIS_RANGE = [ANALYSIS_START_DATE, ANALYSIS_END_DATE]

PAGE_BG = "#ede8de"
PLOT_BG = "#f7f4ee"
GRID = "#d7cec0"
TEXT = "#23362f"
SUBTEXT = "#627168"
ACCENT = "#c06a42"
DEEP_GREEN = "#1f7a6b"

COUNTRY_COLORS = {
    "United States": "#1f7a6b",
    "China": "#4e8b79",
    "India": "#c06a42",
    "Japan": "#9b8b6d",
}

STAGE_COLORS = {
    "Low vaccination (<20%)": "#9fb6a8",
    "Medium vaccination (20%-60%)": "#d7b48c",
    "High vaccination (>=60%)": "#c06a42",
}

STAGE_SHORT = {
    "Low vaccination (<20%)": "Low (<20%)",
    "Medium vaccination (20%-60%)": "Medium (20%-60%)",
    "High vaccination (>=60%)": "High (>=60%)",
}

PEAK_COLORS = {
    "Low (<20%)": "#1f7a6b",
    "High (>=60%)": "#c06a42",
}

CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
}


def read_country_rows(csv_path, usecols, countries):
    frames = []

    for chunk in pd.read_csv(
        csv_path, usecols=usecols, chunksize=CHUNKSIZE, sep=None, engine="python"
    ):
        chunk = chunk[chunk["country"].isin(countries)]

        if "date" in chunk.columns:
            chunk["date"] = pd.to_datetime(chunk["date"], errors="coerce")
            chunk = chunk[
                (chunk["date"] >= ANALYSIS_START_DATE)
                & (chunk["date"] <= ANALYSIS_END_DATE)
            ]

        frames.append(chunk)

    if not frames:
        raise ValueError(f"No target countries found in {csv_path}")

    df = pd.concat(frames, ignore_index=True)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    return df


def apply_theme(fig, title, height=800, legend_orientation="h"):
    fig.update_layout(
        title=dict(text=title, x=0.03, xanchor="left", font=dict(size=23, color=TEXT)),
        height=height,
        template="plotly_white",
        paper_bgcolor=PAGE_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(family="Inter, Segoe UI, Arial, sans-serif", color=TEXT, size=13),
        margin=dict(l=72, r=68, t=88, b=64),
        hoverlabel=dict(
            bgcolor="#fffdf8", bordercolor="#d7cec0", font=dict(color=TEXT)
        ),
        legend=dict(
            orientation=legend_orientation,
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            bgcolor="rgba(247,244,238,0.86)",
            bordercolor="#cfc6b7",
            borderwidth=1,
            font=dict(color=TEXT, size=12),
            title_font=dict(color=TEXT, size=12),
        ),
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor=GRID,
        zeroline=False,
        showline=True,
        linecolor="#b8b0a4",
        tickfont=dict(color=SUBTEXT),
        title_font=dict(color=TEXT),
        ticks="outside",
        ticklen=4,
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor=GRID,
        zeroline=False,
        showline=True,
        linecolor="#b8b0a4",
        tickfont=dict(color=SUBTEXT),
        title_font=dict(color=TEXT),
        ticks="outside",
        ticklen=4,
    )


def set_date_axis(fig):
    fig.update_xaxes(
        range=DATE_AXIS_RANGE, tickformat="%Y", dtick="M12", tick0="2020-01-01"
    )


def safe_spearman_corr(x, y):
    temp = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(temp) < 30:
        return np.nan
    if temp["x"].nunique() <= 1 or temp["y"].nunique() <= 1:
        return np.nan
    return temp["x"].rank().corr(temp["y"].rank(), method="pearson")


def interpret_corr(x):
    if pd.isna(x):
        return "Not enough data"
    if x <= -0.5:
        return "Strong negative relationship"
    if x <= -0.3:
        return "Moderate negative relationship"
    if x < -0.1:
        return "Weak negative relationship"
    if x < 0.1:
        return "No clear relationship"
    if x < 0.3:
        return "Weak positive relationship"
    if x < 0.5:
        return "Moderate positive relationship"
    return "Strong positive relationship"


def write_chart(fig, filename):
    fig.write_html(OUTPUT_DIR / filename, include_plotlyjs="cdn", config=CONFIG)


def relationship_stats(data, x_col, y_col, label):
    temp = data[[x_col, y_col]].replace([np.inf, -np.inf], np.nan).dropna()

    if len(temp) < 3:
        return {
            "pair": label,
            "pearson_r": np.nan,
            "spearman_rho": np.nan,
            "r2": np.nan,
            "n": len(temp),
        }

    pearson = temp[x_col].corr(temp[y_col], method="pearson")
    spearman = temp[x_col].corr(temp[y_col], method="spearman")
    r2 = pearson**2

    return {
        "pair": label,
        "pearson_r": round(pearson, 4),
        "spearman_rho": round(spearman, 4),
        "r2": round(r2, 4),
        "n": len(temp),
    }


def save_quantitative_summary():
    """
    Generate the quantitative summary tables used in the frontend summary section.
    Outputs:
    - country_level_summary.csv
    - relationship_summary.csv
    """

    compact_summary_file = DATA_DIR / "processed_data" / "cleaned_compact.csv"

    if not compact_summary_file.exists():
        compact_summary_file = COMPACT_FILE

    summary_df = pd.read_csv(compact_summary_file, sep=None, engine="python")

    required_cols = [
        "country",
        "date",
        "population",
        "people_vaccinated",
        "new_cases_smoothed",
        "new_deaths_smoothed",
    ]

    missing_cols = [col for col in required_cols if col not in summary_df.columns]
    if missing_cols:
        raise ValueError(
            f"Missing required columns for quantitative summary: {missing_cols}"
        )

    summary_df["date"] = pd.to_datetime(summary_df["date"], errors="coerce")
    summary_df = summary_df[
        (summary_df["date"] >= ANALYSIS_START_DATE)
        & (summary_df["date"] <= ANALYSIS_END_DATE)
    ].copy()
    summary_df = summary_df[summary_df["country"].isin(COUNTRIES)].copy()

    numeric_cols = [
        "population",
        "people_vaccinated",
        "new_cases_smoothed",
        "new_deaths_smoothed",
    ]

    for col in numeric_cols:
        summary_df[col] = pd.to_numeric(summary_df[col], errors="coerce")

    summary_df["vaccinated_pct"] = (
        summary_df["people_vaccinated"] / summary_df["population"] * 100
    )
    summary_df["cases_per_100k"] = (
        summary_df["new_cases_smoothed"] / summary_df["population"] * 100_000
    )
    summary_df["deaths_per_100k"] = (
        summary_df["new_deaths_smoothed"] / summary_df["population"] * 100_000
    )

    summary_df = summary_df.sort_values(["country", "date"])

    summary_df["future_cases_14d"] = summary_df.groupby("country")[
        "cases_per_100k"
    ].shift(-14)
    summary_df["future_cases_28d"] = summary_df.groupby("country")[
        "cases_per_100k"
    ].shift(-28)

    summary_df["month"] = summary_df["date"].dt.to_period("M").astype(str)

    monthly = summary_df.groupby(["country", "month"], as_index=False).agg(
        vaccinated_pct=("vaccinated_pct", "mean"),
        cases_per_100k=("cases_per_100k", "mean"),
        deaths_per_100k=("deaths_per_100k", "mean"),
    )

    peak_rows = []

    for country in COUNTRIES:
        sub = summary_df[summary_df["country"] == country].dropna(
            subset=["cases_per_100k"]
        )

        if sub.empty:
            peak_rows.append(
                {
                    "country": country,
                    "peak_cases_per_100k": np.nan,
                    "peak_date": "",
                }
            )
            continue

        peak_row = sub.loc[sub["cases_per_100k"].idxmax()]

        peak_rows.append(
            {
                "country": country,
                "peak_cases_per_100k": peak_row["cases_per_100k"],
                "peak_date": peak_row["date"].strftime("%Y-%m-%d"),
            }
        )

    peak_df = pd.DataFrame(peak_rows)

    country_summary = (
        monthly.groupby("country", as_index=False)
        .agg(
            months=("month", "nunique"),
            avg_vaccinated_pct=("vaccinated_pct", "mean"),
            avg_cases_per_100k=("cases_per_100k", "mean"),
            avg_deaths_per_100k=("deaths_per_100k", "mean"),
        )
        .merge(peak_df, on="country", how="left")
    )

    country_summary = country_summary.round(
        {
            "avg_vaccinated_pct": 2,
            "avg_cases_per_100k": 2,
            "avg_deaths_per_100k": 4,
            "peak_cases_per_100k": 2,
        }
    )

    relationship_rows = [
        relationship_stats(
            summary_df,
            "vaccinated_pct",
            "cases_per_100k",
            "Vaccinated % vs Cases/100k",
        ),
        relationship_stats(
            summary_df,
            "vaccinated_pct",
            "future_cases_14d",
            "Vaccinated % vs Future Cases 14d",
        ),
        relationship_stats(
            summary_df,
            "vaccinated_pct",
            "future_cases_28d",
            "Vaccinated % vs Future Cases 28d",
        ),
        relationship_stats(
            summary_df,
            "vaccinated_pct",
            "deaths_per_100k",
            "Vaccinated % vs Deaths/100k",
        ),
    ]

    relationship_summary = pd.DataFrame(relationship_rows)

    country_summary.to_csv(
        OUTPUT_DIR / "country_level_summary.csv",
        index=False,
    )
    relationship_summary.to_csv(
        OUTPUT_DIR / "relationship_summary.csv",
        index=False,
    )

    print("\n===== Country-level Summary =====")
    print(country_summary.to_string(index=False))

    print("\n===== Relationship Summary =====")
    print(relationship_summary.to_string(index=False))

    print("\nSummary files saved:")
    print("-", OUTPUT_DIR / "country_level_summary.csv")
    print("-", OUTPUT_DIR / "relationship_summary.csv")


print("Reading cases data...")
cases = read_country_rows(
    CASES_FILE,
    usecols=[
        "country",
        "date",
        "new_cases",
        "new_cases_per_million",
        "new_cases_7_day_avg_right",
        "new_cases_per_million_7_day_avg_right",
    ],
    countries=COUNTRIES,
)

print("Reading vaccination data...")
vaccines = read_country_rows(
    VACCINE_FILE,
    usecols=[
        "country",
        "date",
        "people_vaccinated_interpolated",
        "daily_people_vaccinated_smoothed_per_hundred",
    ],
    countries=COUNTRIES,
)

print("Reading population data...")
compact = read_country_rows(
    COMPACT_FILE, usecols=["country", "population"], countries=COUNTRIES
)

cases = cases.rename(
    columns={
        "new_cases_per_million_7_day_avg_right": "new_cases_pm_7d",
        "new_cases_7_day_avg_right": "new_cases_7d",
    }
)

for col in ["new_cases", "new_cases_per_million", "new_cases_7d", "new_cases_pm_7d"]:
    cases[col] = pd.to_numeric(cases[col], errors="coerce")

cases["new_cases_pm_7d"] = cases["new_cases_pm_7d"].clip(lower=0)
cases["new_cases_7d"] = cases["new_cases_7d"].clip(lower=0)
vaccines["people_vaccinated_interpolated"] = pd.to_numeric(
    vaccines["people_vaccinated_interpolated"], errors="coerce"
)
compact["population"] = pd.to_numeric(compact["population"], errors="coerce")
population = compact.groupby("country", as_index=False)["population"].max().dropna()

df = cases.merge(
    vaccines[["country", "date", "people_vaccinated_interpolated"]],
    on=["country", "date"],
    how="left",
)

df = df.merge(population, on="country", how="left")
df = df.sort_values(["country", "date"])
df = df[(df["date"] >= ANALYSIS_START_DATE) & (df["date"] <= ANALYSIS_END_DATE)].copy()
df["people_vaccinated_interpolated"] = (
    df.groupby("country")["people_vaccinated_interpolated"].ffill().fillna(0)
)
df["vaccination_rate"] = (
    df["people_vaccinated_interpolated"] / df["population"] * 100
).clip(lower=0, upper=100)

for lag in [0, 14, 28]:
    if lag == 0:
        df[f"new_cases_pm_7d_after_{lag}d"] = df["new_cases_pm_7d"]
    else:
        df[f"new_cases_pm_7d_after_{lag}d"] = df.groupby("country")[
            "new_cases_pm_7d"
        ].shift(-lag)

df["vaccination_stage"] = pd.cut(
    df["vaccination_rate"],
    bins=[-0.01, 20, 60, 100],
    labels=[
        "Low vaccination (<20%)",
        "Medium vaccination (20%-60%)",
        "High vaccination (>=60%)",
    ],
)
df["vaccination_stage_short"] = df["vaccination_stage"].map(STAGE_SHORT)
df["case_slope_14d"] = df.groupby("country")["new_cases_pm_7d"].diff(14) / 14
df.to_csv(OUTPUT_DIR / "merged_cases_vaccination_4countries.csv", index=False)

save_quantitative_summary()

fig1 = make_subplots(
    rows=2,
    cols=2,
    subplot_titles=COUNTRIES,
    specs=[
        [{"secondary_y": True}, {"secondary_y": True}],
        [{"secondary_y": True}, {"secondary_y": True}],
    ],
    vertical_spacing=0.16,
    horizontal_spacing=0.16,
)

for i, country in enumerate(COUNTRIES):
    row = i // 2 + 1
    col = i % 2 + 1
    g = df[df["country"] == country].copy()

    fig1.add_trace(
        go.Scatter(
            x=g["date"],
            y=g["new_cases_pm_7d"],
            mode="lines",
            name="New cases per million",
            line=dict(color=DEEP_GREEN, width=3),
            fill="tozeroy",
            fillcolor="rgba(31,122,107,0.08)",
            showlegend=(i == 0),
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Cases: %{y:.1f}/1M<extra></extra>",
        ),
        row=row,
        col=col,
        secondary_y=False,
    )

    fig1.add_trace(
        go.Scatter(
            x=g["date"],
            y=g["vaccination_rate"],
            mode="lines",
            name="Vaccination rate",
            line=dict(color=ACCENT, width=2.8, dash="dot"),
            showlegend=(i == 0),
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Vaccination: %{y:.1f}%<extra></extra>",
        ),
        row=row,
        col=col,
        secondary_y=True,
    )

    fig1.update_yaxes(
        title_text="New cases per million<br>7-day average" if col == 1 else "",
        row=row,
        col=col,
        secondary_y=False,
    )
    fig1.update_yaxes(
        title_text="Vaccination rate (%)" if col == 2 else "",
        range=[0, 100],
        row=row,
        col=col,
        secondary_y=True,
    )

apply_theme(
    fig1,
    "Vaccination Rate vs New COVID-19 Cases in Four Representative Countries",
    height=960,
)
set_date_axis(fig1)
fig1.update_annotations(font=dict(size=14, color=TEXT))
write_chart(fig1, "01_trend_vaccination_vs_cases.html")

stage_summary = (
    df.dropna(subset=["vaccination_stage", "new_cases_pm_7d"])
    .groupby(["country", "vaccination_stage"], observed=True)
    .agg(
        days=("date", "count"),
        median_new_cases_pm_7d=("new_cases_pm_7d", "median"),
        q25_new_cases_pm_7d=("new_cases_pm_7d", lambda x: x.quantile(0.25)),
        q75_new_cases_pm_7d=("new_cases_pm_7d", lambda x: x.quantile(0.75)),
        mean_new_cases_pm_7d=("new_cases_pm_7d", "mean"),
        peak_new_cases_pm_7d=("new_cases_pm_7d", "max"),
    )
    .reset_index()
)
stage_summary["vaccination_stage_short"] = stage_summary["vaccination_stage"].map(
    STAGE_SHORT
)
stage_summary["iqr_new_cases_pm_7d"] = (
    stage_summary["q75_new_cases_pm_7d"] - stage_summary["q25_new_cases_pm_7d"]
).clip(lower=0)
stage_summary.to_csv(OUTPUT_DIR / "vaccination_stage_summary.csv", index=False)

stage_order = [
    "Low vaccination (<20%)",
    "Medium vaccination (20%-60%)",
    "High vaccination (>=60%)",
]
stage_order_short = [STAGE_SHORT[s] for s in stage_order]
max_iqr = stage_summary["iqr_new_cases_pm_7d"].max()
if pd.isna(max_iqr) or max_iqr <= 0:
    max_iqr = 1

fig2 = go.Figure()

for stage in stage_order:
    g = stage_summary[stage_summary["vaccination_stage"] == stage].copy()
    g["marker_size"] = 28 + (g["iqr_new_cases_pm_7d"] / max_iqr * 34)
    g["median_label"] = g["median_new_cases_pm_7d"].round(0).astype("Int64").astype(str)

    fig2.add_trace(
        go.Scatter(
            x=g["vaccination_stage_short"],
            y=g["country"],
            mode="markers+text",
            name=STAGE_SHORT[stage],
            marker=dict(
                size=g["marker_size"],
                color=STAGE_COLORS[stage],
                opacity=0.86,
                line=dict(width=2.2, color=PLOT_BG),
            ),
            text=g["median_label"],
            textposition="middle center",
            textfont=dict(
                size=12, color=TEXT, family="Inter, Segoe UI, Arial, sans-serif"
            ),
            customdata=np.stack(
                [
                    g["days"],
                    g["q25_new_cases_pm_7d"],
                    g["q75_new_cases_pm_7d"],
                    g["peak_new_cases_pm_7d"],
                ],
                axis=-1,
            ),
            hovertemplate=(
                "Country: %{y}<br>Stage: %{x}<br>Median cases: %{text}/1M"
                "<br>Days: %{customdata[0]}"
                "<br>IQR: %{customdata[1]:.1f}–%{customdata[2]:.1f}/1M"
                "<br>Peak: %{customdata[3]:.1f}/1M<extra></extra>"
            ),
        )
    )

fig2.update_layout(
    legend_title="Vaccination stage",
    xaxis=dict(categoryorder="array", categoryarray=stage_order_short),
    yaxis=dict(categoryorder="array", categoryarray=COUNTRIES[::-1]),
)
fig2.update_xaxes(title_text="Vaccination stage")
fig2.update_yaxes(title_text="Country")
apply_theme(fig2, "New Case Distribution by Vaccination Stage", height=720)
fig2.update_layout(
    margin=dict(l=95, r=60, t=88, b=80),
    annotations=[
        dict(
            x=1.0,
            y=-0.18,
            xref="paper",
            yref="paper",
            showarrow=False,
            xanchor="right",
            text="Bubble text = median cases per million; bubble size = interquartile range.",
            font=dict(size=12, color=SUBTEXT),
        )
    ],
)
write_chart(fig2, "02_cases_by_vaccination_stage.html")

correlation_rows = []

for country in COUNTRIES:
    g = df[df["country"] == country].copy()
    g = g[g["vaccination_rate"] >= 1]

    for lag in [0, 14, 28]:
        y_col = f"new_cases_pm_7d_after_{lag}d"
        temp = g[["vaccination_rate", y_col]].dropna()

        if (
            len(temp) >= 30
            and temp["vaccination_rate"].nunique() > 1
            and temp[y_col].nunique() > 1
        ):
            pearson = temp["vaccination_rate"].corr(temp[y_col], method="pearson")
            spearman = safe_spearman_corr(temp["vaccination_rate"], temp[y_col])
        else:
            pearson = np.nan
            spearman = np.nan

        correlation_rows.append(
            {
                "country": country,
                "lag_days": lag,
                "sample_size": len(temp),
                "pearson_correlation": pearson,
                "spearman_correlation": spearman,
            }
        )

correlation_summary = pd.DataFrame(correlation_rows)
correlation_summary["pearson_interpretation"] = correlation_summary[
    "pearson_correlation"
].apply(interpret_corr)
correlation_summary["spearman_interpretation"] = correlation_summary[
    "spearman_correlation"
].apply(interpret_corr)
correlation_summary.to_csv(OUTPUT_DIR / "correlation_summary.csv", index=False)

fig3 = make_subplots(
    rows=2,
    cols=2,
    subplot_titles=COUNTRIES,
    vertical_spacing=0.16,
    horizontal_spacing=0.14,
)

for i, country in enumerate(COUNTRIES):
    row = i // 2 + 1
    col = i % 2 + 1
    g = df[(df["country"] == country) & (df["vaccination_rate"] >= 1)].dropna(
        subset=["vaccination_rate", "new_cases_pm_7d_after_28d"]
    )
    g = g.copy()
    g["log_cases_28d"] = np.log10(g["new_cases_pm_7d_after_28d"].clip(lower=0) + 1)
    color = COUNTRY_COLORS[country]

    fig3.add_trace(
        go.Scatter(
            x=g["vaccination_rate"],
            y=g["log_cases_28d"],
            mode="markers",
            name=country,
            marker=dict(
                size=4.6,
                color=color,
                opacity=0.36,
                line=dict(width=0.45, color="rgba(255,255,255,0.55)"),
            ),
            showlegend=False,
            hovertemplate="Vaccination: %{x:.1f}%<br>log10(cases+1): %{y:.2f}<extra></extra>",
        ),
        row=row,
        col=col,
    )

    pearson_text = "N/A"
    spearman_text = "N/A"

    if len(g) >= 30 and g["vaccination_rate"].nunique() > 1:
        temp_corr = g[["vaccination_rate", "new_cases_pm_7d_after_28d"]].dropna()
        if len(temp_corr) >= 30:
            pearson_value = temp_corr["vaccination_rate"].corr(
                temp_corr["new_cases_pm_7d_after_28d"], method="pearson"
            )
            spearman_value = safe_spearman_corr(
                temp_corr["vaccination_rate"], temp_corr["new_cases_pm_7d_after_28d"]
            )
            pearson_text = f"{pearson_value:.3f}" if pd.notna(pearson_value) else "N/A"
            spearman_text = (
                f"{spearman_value:.3f}" if pd.notna(spearman_value) else "N/A"
            )

        g["bin"] = pd.cut(
            g["vaccination_rate"], bins=np.linspace(0, 100, 11), include_lowest=True
        )
        binned = (
            g.groupby("bin", observed=True)
            .agg(
                vaccination_rate=("vaccination_rate", "median"),
                log_cases_28d=("log_cases_28d", "median"),
                n=("log_cases_28d", "count"),
            )
            .reset_index()
        )
        binned = binned[binned["n"] >= 8]

        if len(binned) >= 2:
            fig3.add_trace(
                go.Scatter(
                    x=binned["vaccination_rate"],
                    y=binned["log_cases_28d"],
                    mode="lines+markers",
                    name=f"{country} binned median",
                    line=dict(color=color, width=3.5),
                    marker=dict(
                        size=7.5, color=PLOT_BG, line=dict(width=2, color=color)
                    ),
                    showlegend=False,
                    hovertemplate="Median vaccination: %{x:.1f}%<br>Median log cases: %{y:.2f}<extra></extra>",
                ),
                row=row,
                col=col,
            )

    axis_index = i + 1
    xref = "x domain" if axis_index == 1 else f"x{axis_index} domain"
    yref = "y domain" if axis_index == 1 else f"y{axis_index} domain"
    fig3.add_annotation(
        x=0.03,
        y=0.95,
        xref=xref,
        yref=yref,
        text=f"Pearson r = {pearson_text}<br>Spearman r = {spearman_text}",
        showarrow=False,
        align="left",
        font=dict(size=11, color=SUBTEXT),
        bgcolor="rgba(255,250,242,0.90)",
        bordercolor=color,
        borderwidth=1,
    )

    fig3.update_xaxes(
        title_text="Vaccination rate (%)", range=[0, 100], row=row, col=col
    )
    fig3.update_yaxes(
        title_text="log10(new cases + 1)<br>28 days later" if col == 1 else "",
        row=row,
        col=col,
    )

apply_theme(
    fig3,
    "Relationship between Vaccination Rate and New Cases after 28 Days",
    height=940,
)
fig3.update_annotations(font=dict(size=14, color=TEXT))
write_chart(fig3, "03_correlation_scatter_28day_lag.html")

fig4 = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=False,
    vertical_spacing=0.18,
    subplot_titles=[
        "New cases per million over time",
        "Vaccination milestone comparison",
    ],
    row_heights=[0.62, 0.38],
)

for country in COUNTRIES:
    g = df[df["country"] == country].copy()
    color = COUNTRY_COLORS[country]
    fig4.add_trace(
        go.Scatter(
            x=g["date"],
            y=g["new_cases_pm_7d"],
            mode="lines",
            name=country,
            line=dict(color=color, width=2.8),
            hovertemplate=f"{country}<br>Date: %{{x|%Y-%m-%d}}<br>Cases: %{{y:.1f}}/1M<extra></extra>",
        ),
        row=1,
        col=1,
    )

milestones = []
for country in COUNTRIES:
    g = df[df["country"] == country].sort_values("date")
    for threshold in [20, 60, 80]:
        reached = g[g["vaccination_rate"] >= threshold]
        if not reached.empty:
            milestones.append(
                {
                    "country": country,
                    "threshold": f"{threshold}%",
                    "threshold_value": threshold,
                    "date": reached.iloc[0]["date"],
                }
            )

milestone_df = pd.DataFrame(milestones)
milestone_df.to_csv(OUTPUT_DIR / "vaccination_milestone_summary.csv", index=False)

threshold_symbols = {20: "circle", 60: "diamond", 80: "square"}
threshold_sizes = {20: 12, 60: 14, 80: 13}

for threshold in [20, 60, 80]:
    g = milestone_df[milestone_df["threshold_value"] == threshold]
    fig4.add_trace(
        go.Scatter(
            x=g["date"],
            y=g["country"],
            mode="markers+text",
            name=f"Reached {threshold}%",
            marker=dict(
                size=threshold_sizes[threshold],
                symbol=threshold_symbols[threshold],
                color=ACCENT if threshold == 80 else DEEP_GREEN,
                opacity=0.9,
                line=dict(width=1.5, color=PLOT_BG),
            ),
            text=g["threshold"],
            textposition="top center",
            textfont=dict(size=11, color=TEXT),
            hovertemplate="%{y}<br>Reached %{text}: %{x|%Y-%m-%d}<extra></extra>",
        ),
        row=2,
        col=1,
    )

for country in COUNTRIES:
    g = milestone_df[milestone_df["country"] == country].sort_values("date")
    if len(g) >= 2:
        fig4.add_trace(
            go.Scatter(
                x=g["date"],
                y=g["country"],
                mode="lines",
                line=dict(color="rgba(31,122,107,0.28)", width=4),
                showlegend=False,
                hoverinfo="skip",
            ),
            row=2,
            col=1,
        )

fig4.update_yaxes(title_text="New cases per million<br>7-day average", row=1, col=1)
fig4.update_yaxes(
    title_text="Country",
    categoryorder="array",
    categoryarray=COUNTRIES[::-1],
    row=2,
    col=1,
)
fig4.update_xaxes(
    title_text="Date",
    range=DATE_AXIS_RANGE,
    tickformat="%Y",
    dtick="M12",
    tick0="2020-01-01",
    row=1,
    col=1,
)
fig4.update_xaxes(
    title_text="Date when milestone was first reached",
    range=DATE_AXIS_RANGE,
    tickformat="%Y",
    dtick="M12",
    tick0="2020-01-01",
    row=2,
    col=1,
)

apply_theme(
    fig4, "Cross-country Comparison: Case Waves and Vaccination Milestones", height=900
)
fig4.update_layout(
    legend_title="Country / milestone",
    legend=dict(orientation="h", y=1.02, x=1.0, xanchor="right"),
)
fig4.update_annotations(font=dict(size=14, color=TEXT))
write_chart(fig4, "04_cross_country_comparison.html")

peak_rows = []

for country in COUNTRIES:
    g_country = df[df["country"] == country].copy()

    for stage_name in ["Low vaccination (<20%)", "High vaccination (>=60%)"]:
        g_stage = g_country[g_country["vaccination_stage"] == stage_name].dropna(
            subset=["new_cases_pm_7d"]
        )

        if len(g_stage) == 0:
            peak_rows.append(
                {
                    "country": country,
                    "vaccination_stage": stage_name,
                    "vaccination_stage_short": STAGE_SHORT[stage_name],
                    "days": 0,
                    "peak_new_cases_pm_7d": np.nan,
                    "peak_date": None,
                    "median_new_cases_pm_7d": np.nan,
                    "max_14d_rise_per_day": np.nan,
                }
            )
            continue

        peak_idx = g_stage["new_cases_pm_7d"].idxmax()
        peak_rows.append(
            {
                "country": country,
                "vaccination_stage": stage_name,
                "vaccination_stage_short": STAGE_SHORT[stage_name],
                "days": len(g_stage),
                "peak_new_cases_pm_7d": g_stage.loc[peak_idx, "new_cases_pm_7d"],
                "peak_date": g_stage.loc[peak_idx, "date"],
                "median_new_cases_pm_7d": g_stage["new_cases_pm_7d"].median(),
                "max_14d_rise_per_day": g_stage["case_slope_14d"].max(),
            }
        )

peak_summary = pd.DataFrame(peak_rows)
peak_summary.to_csv(OUTPUT_DIR / "peak_summary.csv", index=False)

fig5 = go.Figure()
for stage in [
    STAGE_SHORT["Low vaccination (<20%)"],
    STAGE_SHORT["High vaccination (>=60%)"],
]:
    g = peak_summary[peak_summary["vaccination_stage_short"] == stage]
    fig5.add_trace(
        go.Bar(
            x=g["country"],
            y=g["peak_new_cases_pm_7d"],
            name=stage,
            marker=dict(color=PEAK_COLORS[stage], line=dict(width=0)),
            opacity=0.94,
            text=g["peak_new_cases_pm_7d"].round(0),
            texttemplate="%{text:.0f}",
            textposition="outside",
            hovertemplate="Country: %{x}<br>Peak cases: %{y:.1f}/1M<extra></extra>",
        )
    )

fig5.update_layout(barmode="group", bargap=0.32, bargroupgap=0.12)
fig5.update_yaxes(title_text="Peak new cases per million<br>7-day average")
fig5.update_xaxes(title_text="Country", categoryorder="array", categoryarray=COUNTRIES)
apply_theme(fig5, "Peak Cases before vs after Broad Vaccination", height=680)
fig5.update_layout(legend_title="Vaccination stage")
write_chart(fig5, "05_peak_before_after_rollout.html")

fig6 = make_subplots(
    rows=2,
    cols=2,
    subplot_titles=COUNTRIES,
    vertical_spacing=0.16,
    horizontal_spacing=0.14,
)

for i, country in enumerate(COUNTRIES):
    row = i // 2 + 1
    col = i % 2 + 1
    g = df[df["country"] == country].copy()
    color = COUNTRY_COLORS[country]

    fig6.add_trace(
        go.Scatter(
            x=g["date"],
            y=g["new_cases_pm_7d"],
            mode="lines",
            name=country,
            line=dict(color=color, width=2.8),
            fill="tozeroy",
            fillcolor="rgba(31,122,107,0.06)",
            showlegend=False,
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Cases: %{y:.1f}/1M<extra></extra>",
        ),
        row=row,
        col=col,
    )

    y_top = g["new_cases_pm_7d"].max()
    if pd.isna(y_top) or y_top == 0:
        y_top = 1

    for threshold, threshold_color, y_pos_ratio in [
        (20, "#1f7a6b", 0.92),
        (60, "#d96b2b", 0.78),
    ]:
        threshold_data = g[g["vaccination_rate"] >= threshold]
        if not threshold_data.empty:
            threshold_date = threshold_data["date"].min()
            fig6.add_shape(
                type="line",
                x0=threshold_date,
                x1=threshold_date,
                y0=0,
                y1=y_top,
                line=dict(color=threshold_color, width=2.2, dash="dot"),
                row=row,
                col=col,
            )
            fig6.add_annotation(
                x=threshold_date,
                y=y_top * y_pos_ratio,
                text=f"{threshold}%",
                showarrow=False,
                font=dict(size=10, color=TEXT),
                bgcolor="rgba(247,244,238,0.88)",
                bordercolor=threshold_color,
                borderwidth=1,
                row=row,
                col=col,
            )

    fig6.update_yaxes(
        title_text="New cases per million<br>7-day average" if col == 1 else "",
        row=row,
        col=col,
    )

apply_theme(fig6, "Epidemic Waves with Vaccination Thresholds", height=920)
set_date_axis(fig6)
fig6.update_annotations(font=dict(size=14, color=TEXT))
write_chart(fig6, "06_waves_with_vaccination_thresholds.html")

print("\nAnalysis completed.")
print(f"Output folder: {OUTPUT_DIR}")
print("\nGenerated files:")
for file in sorted(OUTPUT_DIR.iterdir()):
    print("-", file.name)
