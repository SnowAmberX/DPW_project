from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd
from plotly.subplots import make_subplots

from _shared import TIMELINE_MONTH_END, latest_age_breakdown, load_compact, write_figure

TITLE_TEMPLATE = "Age-group Vaccination and Vulnerability: {country}"

# Canonical age bands (same Y-axis for every country): match France OWID buckets.
FRANCE_BUCKETS = ["0-17", "18-24", "25-49", "50-59", "60-69", "70-79", "80+"]

FRANCE_INTERVALS = [
    ("0-17", 0.0, 17.0),
    ("18-24", 18.0, 24.0),
    ("25-49", 25.0, 49.0),
    ("50-59", 50.0, 59.0),
    ("60-69", 60.0, 69.0),
    ("70-79", 70.0, 79.0),
    ("80+", 80.0, 120.0),
]

# Mid-age within each France bucket for mortality-weight scaling (same formula as before).
FRANCE_MID_AGE = {
    "0-17": 8.5,
    "18-24": 21.0,
    "25-49": 37.0,
    "50-59": 54.5,
    "60-69": 64.5,
    "70-79": 74.5,
    "80+": 85.0,
}


def _monthly_mean_deaths_by_country() -> pd.DataFrame:
    raw = load_compact()
    raw = raw[raw["month"] <= TIMELINE_MONTH_END].copy()
    return (
        raw.groupby(["country", "month"], as_index=False)
        .agg(deaths_per_100k=("deaths_per_100k", "mean"))
        .sort_values(["country", "month"])
    )


def _mortality_baseline(monthly_full: pd.DataFrame, country: str) -> float:
    """Use last month with positive deaths (avoids trailing zeros)."""
    g = monthly_full[monthly_full["country"] == country].sort_values("month")
    if g.empty:
        return 0.0
    for v in g["deaths_per_100k"].to_numpy()[::-1]:
        fv = float(v)
        if fv > 1e-9:
            return fv
    return float(g["deaths_per_100k"].iloc[-1])


def _source_age_interval(age_group: str) -> tuple[float, float]:
    ag = age_group.strip()
    if ag.endswith("+"):
        return float(ag[:-1]), 120.0
    if "-" in ag:
        a, b = ag.split("-", 1)
        return float(a), float(b)
    return float(ag), float(ag)


def _overlapping_france_labels(lo: float, hi: float) -> list[str]:
    out = []
    for name, fl, fh in FRANCE_INTERVALS:
        if max(lo, fl) <= min(hi, fh):
            out.append(name)
    return out


def align_to_france_buckets(country_df: pd.DataFrame, baseline: float) -> pd.DataFrame:
    """
    Map each country's native age_group rows onto France's 7 buckets.
    Overlapping source intervals contribute the same reported % to each overlapped bucket;
    multiple rows targeting one bucket are averaged.
    """
    rows = []
    for _, row in country_df.iterrows():
        lo, hi = _source_age_interval(str(row["age_group"]))
        targets = _overlapping_france_labels(lo, hi)
        for t in targets:
            rows.append(
                {
                    "age_group": t,
                    "people_vaccinated_per_hundred": float(row["people_vaccinated_per_hundred"]),
                    "people_fully_vaccinated_per_hundred": float(row["people_fully_vaccinated_per_hundred"]),
                    "people_with_booster_per_hundred": float(row["people_with_booster_per_hundred"]),
                }
            )
    if not rows:
        agg = pd.DataFrame(
            columns=[
                "age_group",
                "people_vaccinated_per_hundred",
                "people_fully_vaccinated_per_hundred",
                "people_with_booster_per_hundred",
            ]
        )
    else:
        agg = pd.DataFrame(rows).groupby("age_group", as_index=False).mean(numeric_only=True)

    base = pd.DataFrame({"age_group": FRANCE_BUCKETS})
    merged = base.merge(agg, on="age_group", how="left")
    for col in (
        "people_vaccinated_per_hundred",
        "people_fully_vaccinated_per_hundred",
        "people_with_booster_per_hundred",
    ):
        merged[col] = merged[col].fillna(0.0)
    merged["risk_proxy"] = merged["age_group"].map(
        lambda g: baseline
        * max(0.18, min(2.6, ((FRANCE_MID_AGE[g] + 10) / 42) ** 1.45))
    )
    merged["age_start"] = range(len(FRANCE_BUCKETS))
    return merged


def build() -> None:
    monthly_full = _monthly_mean_deaths_by_country()
    age_source_countries = [
        "Japan",
        "France",
        "Italy",
        "Spain",
        "Portugal",
        "Poland",
        "Sweden",
        "Netherlands",
    ]
    age_df = latest_age_breakdown(age_source_countries)

    country_options = sorted(age_df["country"].unique().tolist())
    fig = make_subplots(
        rows=1,
        cols=2,
        column_widths=[0.72, 0.28],
        horizontal_spacing=0.06,
        specs=[[{"type": "bar"}, {"type": "scatter"}]],
    )
    traces_per_country = 4
    buttons = []

    # Global vulnerability index range across all countries for one shared color scale / colorbar readability
    rp_global_min = float("inf")
    rp_global_max = float("-inf")
    aligned_cache: dict[str, pd.DataFrame] = {}
    for country in country_options:
        raw_c = age_df[age_df["country"] == country].copy()
        bl = _mortality_baseline(monthly_full, country)
        aligned = align_to_france_buckets(raw_c, bl)
        aligned_cache[country] = aligned
        rp_global_min = min(rp_global_min, float(aligned["risk_proxy"].min()))
        rp_global_max = max(rp_global_max, float(aligned["risk_proxy"].max()))
    if not (rp_global_max > rp_global_min):
        rp_global_max = rp_global_min + 1e-9

    for idx, country in enumerate(country_options):
        subset = aligned_cache[country]
        dose = subset["people_vaccinated_per_hundred"].astype(float)
        full = subset["people_fully_vaccinated_per_hundred"].astype(float)
        boost = subset["people_with_booster_per_hundred"].astype(float)
        yvals = subset["age_group"]
        visible = idx == 0

        fig.add_trace(
            go.Bar(
                x=dose.clip(0, 100),
                y=yvals,
                orientation="h",
                name="At least one dose",
                marker_color="#1d6b57",
                visible=visible,
                customdata=dose,
                hovertemplate="%{y}<br>At least one dose: %{customdata:.1f}%<extra></extra>",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Bar(
                x=full.clip(0, 100),
                y=yvals,
                orientation="h",
                name="Fully vaccinated",
                marker_color="#62a692",
                visible=visible,
                customdata=full,
                hovertemplate="%{y}<br>Fully vaccinated: %{customdata:.1f}%<extra></extra>",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Bar(
                x=boost.clip(0, 100),
                y=yvals,
                orientation="h",
                name="Booster",
                marker_color="#c86d45",
                visible=visible,
                customdata=boost,
                hovertemplate="%{y}<br>Booster: %{customdata:.1f}%<extra></extra>",
            ),
            row=1,
            col=1,
        )
        rp = subset["risk_proxy"].astype(float)
        rp_span = float(rp.max() - rp.min())
        if rp_span > 1e-12:
            x_spread = 0.03 + 0.94 * (rp - rp.min()) / rp_span
        else:
            x_spread = pd.Series(0.5, index=rp.index)
        rp_vals = rp.tolist()

        fig.add_trace(
            go.Scatter(
                x=x_spread,
                y=yvals,
                mode="markers+text",
                name="Relative vulnerability",
                marker=dict(
                    color=rp,
                    cmin=rp_global_min,
                    cmax=rp_global_max,
                    size=18,
                    symbol="diamond",
                    colorscale=[[0, "#d7e6df"], [0.5, "#9ab9ad"], [1, "#597a6c"]],
                    showscale=True,
                    colorbar=dict(
                        title=dict(text="Relative vulnerability index", side="right"),
                        thickness=14,
                        len=0.62,
                        x=1.02,
                        xanchor="left",
                        bgcolor="rgba(255,250,242,0.92)",
                        tickformat=".4f",
                    ),
                    line=dict(width=1, color="#fffaf2"),
                ),
                customdata=rp_vals,
                text=[
                    "Very high" if value > 0.12 else "High" if value > 0.05 else "Moderate" if value > 0.01 else "Lower"
                    for value in rp_vals
                ],
                textposition="top center",
                visible=visible,
                hovertemplate="%{y}<br>Relative vulnerability: %{customdata:.4f}<extra></extra>",
            ),
            row=1,
            col=2,
        )

        vis = [False] * (len(country_options) * traces_per_country)
        for offset in range(traces_per_country):
            vis[idx * traces_per_country + offset] = True
        buttons.append(
            dict(
                label=country,
                method="update",
                args=[
                    {"visible": vis},
                    {"title.text": TITLE_TEMPLATE.format(country=country)},
                ],
            )
        )

    fig.update_layout(
        title=dict(
            text=TITLE_TEMPLATE.format(country=country_options[0]),
            font=dict(size=17, color="#1f2a1f"),
            x=0.5,
            xanchor="center",
        ),
        barmode="group",
        updatemenus=[
            dict(buttons=buttons, x=1, xanchor="right", y=1.16, yanchor="top", active=0)
        ],
        xaxis=dict(title="Vaccination coverage (%)", showgrid=True, gridcolor="#e8decd"),
        xaxis2=dict(
            title="Relative vulnerability",
            range=[0, 1],
            showgrid=True,
            gridcolor="rgba(232, 222, 205, 0.55)",
            showticklabels=False,
            zeroline=False,
        ),
        legend=dict(orientation="h", y=-0.2),
    )
    fig.update_yaxes(autorange="reversed", categoryorder="array", categoryarray=FRANCE_BUCKETS)
    fig.update_traces(selector=dict(type="bar"), width=0.22)
    write_figure(fig, "age-risk-context.html", height=680, margin=dict(l=56, r=108, t=72, b=72))


if __name__ == "__main__":
    build()
