from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd

from _shared import TIMELINE_MONTH_END, monthly_compact, write_figure

# Row order: World → continents (A–Z) → income bands (A–Z) → countries (A–Z).
_CONTINENT_NAMES = frozenset(
    {
        "Africa",
        "Asia",
        "Europe",
        "European Union (27)",
        "North America",
        "Oceania",
        "South America",
    }
)

_INCOME_NAMES = frozenset(
    {
        "High-income countries",
        "Low-income countries",
        "Lower-middle-income countries",
        "Upper-middle-income countries",
    }
)


def _heatmap_row_sort_key(name: str) -> tuple[int, str]:
    lowered = name.lower()
    if name == "World":
        return (0, lowered)
    if name in _CONTINENT_NAMES:
        return (1, lowered)
    if name in _INCOME_NAMES:
        return (2, lowered)
    return (3, lowered)


def build() -> None:
    df = monthly_compact()
    df = df[df["month"] <= TIMELINE_MONTH_END].copy()
    df["quarter"] = pd.PeriodIndex(df["month"], freq="M").asfreq("Q").astype(str)
    quarter_df = (
        df.groupby(["country", "quarter"], as_index=False)
        .agg(
            deaths_per_100k=("deaths_per_100k", "mean"),
            vaccinated_pct=("vaccinated_pct", "mean"),
            cases_per_100k=("cases_per_100k", "mean"),
            population=("population", "max"),
        )
        .sort_values(["quarter", "country"])
    )

    # Same x-range for all three toggles: quarters where vaccinated_pct has signal, capped at end of 2023.
    shared_quarters = (
        quarter_df.groupby("quarter")["vaccinated_pct"].sum().reset_index().query("vaccinated_pct > 0")["quarter"].tolist()
    )
    shared_quarters = [q for q in shared_quarters if q <= "2023Q4"]
    if not shared_quarters:
        shared_quarters = sorted(quarter_df["quarter"].unique().tolist())

    fig = go.Figure()
    metric_specs = [
        ("Mortality Patterns", "deaths_per_100k", [[0, "#fbf2ec"], [0.45, "#efc2ad"], [1, "#c86d45"]]),
        ("Vaccination Coverage", "vaccinated_pct", [[0, "#edf5f1"], [0.45, "#9fcdbd"], [1, "#1d6b57"]]),
        ("Case Pressure", "cases_per_100k", [[0, "#fcf3e8"], [0.45, "#efc89d"], [1, "#b85c38"]]),
    ]

    for idx, (label, metric_key, scale) in enumerate(metric_specs):
        metric_df = quarter_df.copy()
        latest_quarter = shared_quarters[-1]
        latest_slice = metric_df[metric_df["quarter"] == latest_quarter].sort_values(metric_key, ascending=False)
        raw_top = latest_slice["country"].head(8).tolist()
        countries = sorted(raw_top, key=_heatmap_row_sort_key)
        subset = metric_df[metric_df["country"].isin(countries) & metric_df["quarter"].isin(shared_quarters)].copy()
        pivot = subset.pivot(index="country", columns="quarter", values=metric_key).reindex(countries)[shared_quarters]
        quarter_labels = [quarter.replace("Q", "-Q") for quarter in shared_quarters]

        fig.add_trace(
            go.Heatmap(
                z=pivot.values,
                x=quarter_labels,
                y=list(pivot.index),
                colorscale=scale,
                visible=idx == 0,
                colorbar=dict(title=label, thickness=14, len=0.76, y=0.5),
                xgap=6,
                ygap=6,
                hovertemplate="Country: %{y}<br>Month: %{x}<br>Value: %{z:.2f}<extra></extra>",
            )
        )

    buttons = []
    for idx, (label, _, _) in enumerate(metric_specs):
        vis = [False] * len(metric_specs)
        vis[idx] = True
        buttons.append(
            dict(
                label=label,
                method="update",
                args=[
                    {"visible": vis},
                    # Keep the main title stable; the active metric is shown on the colorbar + button label.
                    {"title.text": "Cross-country Pandemic Patterns"},
                ],
            )
        )

    default_labels = [quarter.replace("Q", "-Q") for quarter in shared_quarters]

    fig.update_layout(
        title=dict(
            text="Cross-country Pandemic Patterns",
            font=dict(size=17, color="#1f2a1f"),
            x=0.5,
            xanchor="center",
        ),
        updatemenus=[
            dict(buttons=buttons, x=1, xanchor="right", y=1.12, yanchor="top", active=0)
        ],
        xaxis=dict(
            title="Pandemic timeline by quarter",
            tickangle=-30,
            side="bottom",
            tickmode="array",
            tickvals=[label for index, label in enumerate(default_labels) if index % 2 == 0],
            ticktext=[label for index, label in enumerate(default_labels) if index % 2 == 0],
        ),
        yaxis=dict(title="", autorange="reversed"),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    write_figure(fig, "heatmap-matrix.html", height=620)


if __name__ == "__main__":
    build()
