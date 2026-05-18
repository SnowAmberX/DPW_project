from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from _shared import TIMELINE_MONTH_END, monthly_compact, write_figure

# Fixed y-axis entities (same rows for 30% / 50% / 70% toggles): global, continents, union, countries, income band.
# All must pass the 3-month-before / 3-month-after window at every threshold used below.
FIXED_PANEL_ORDER = [
    "World",
    "South America",
    "Asia",
    "European Union (27)",
    "Brazil",
    "United States",
    "Germany",
    "Upper-middle-income countries",
]

THRESHOLDS = (30, 50, 70)
DEFAULT_THRESHOLD_INDEX = 1  # 50% — must match initial trace visibility

TITLE_TEMPLATE = "Mortality Change After Vaccination Threshold: {pct}%"


def threshold_row(df: pd.DataFrame, country: str, threshold: int) -> dict | None:
    group = df[df["country"] == country].sort_values("month").reset_index(drop=True)
    if len(group) < 5:
        return None
    hit = group.index[group["vaccinated_pct"] >= threshold]
    if len(hit) == 0:
        return None
    idx = int(hit[0])
    if idx < 3 or idx + 2 >= len(group):
        return None
    before = group.loc[idx - 3 : idx - 1, "deaths_per_100k"].mean()
    after = group.loc[idx : idx + 2, "deaths_per_100k"].mean()
    return {
        "country": country,
        "threshold_month": group.loc[idx, "month"],
        "before": before,
        "after": after,
        "reduction": before - after,
    }


def build_panel_df(df: pd.DataFrame, threshold: int, panel: list[str]) -> pd.DataFrame:
    rows = []
    for country in panel:
        r = threshold_row(df, country, threshold)
        if r is None:
            continue
        rows.append(r)
    if not rows:
        return pd.DataFrame(
            columns=["country", "threshold_month", "before", "after", "reduction"]
        )
    out = pd.DataFrame(rows)
    out["country"] = pd.Categorical(out["country"], categories=panel, ordered=True)
    return out.sort_values("country")


def build() -> None:
    df = monthly_compact()
    df = df[df["month"] <= TIMELINE_MONTH_END].copy()
    panel = [c for c in FIXED_PANEL_ORDER if all(threshold_row(df, c, t) is not None for t in THRESHOLDS)]

    ranked_by_threshold: dict[int, pd.DataFrame] = {}
    all_reductions: list[float] = []
    for threshold in THRESHOLDS:
        ranked_by_threshold[threshold] = build_panel_df(df, threshold, panel)
        r = ranked_by_threshold[threshold]
        if not r.empty:
            all_reductions.extend(r["reduction"].astype(float).tolist())
    if all_reductions:
        lo, hi = min(all_reductions), max(all_reductions)
        pad = max(abs(lo), abs(hi), 0.02) * 0.12 + 0.01
        x2_min = min(0.0, lo - pad)
        x2_max = max(0.0, hi + pad)
    else:
        x2_min, x2_max = -0.05, 0.05

    fig = make_subplots(
        rows=1,
        cols=2,
        column_widths=[0.72, 0.28],
        horizontal_spacing=0.08,
        specs=[[{"type": "bar"}, {"type": "scatter"}]],
    )

    traces_per_threshold = 3
    for threshold_index, threshold in enumerate(THRESHOLDS):
        ranked = ranked_by_threshold[threshold]
        visible = threshold_index == DEFAULT_THRESHOLD_INDEX
        if ranked.empty:
            ranked = pd.DataFrame(
                {
                    "country": panel,
                    "threshold_month": [""] * len(panel),
                    "before": [0.0] * len(panel),
                    "after": [0.0] * len(panel),
                    "reduction": [0.0] * len(panel),
                }
            )
        fig.add_trace(
            go.Bar(
                x=ranked["before"],
                y=ranked["country"],
                orientation="h",
                name="Before threshold",
                marker_color="#c86d45",
                visible=visible,
                customdata=ranked[["threshold_month"]],
                hovertemplate="%{y}<br>Before: %{x:.3f}<br>Threshold month: %{customdata[0]}<extra></extra>",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Bar(
                x=ranked["after"],
                y=ranked["country"],
                orientation="h",
                name="After threshold",
                marker_color="#1d6b57",
                visible=visible,
                customdata=ranked[["reduction"]],
                hovertemplate="%{y}<br>After: %{x:.3f}<br>Reduction: %{customdata[0]:.3f}<extra></extra>",
            ),
            row=1,
            col=1,
        )
        reds = ranked["reduction"].astype(float)
        marker_colors = ["#1d6b57" if v >= 0 else "#b85c38" for v in reds]
        fig.add_trace(
            go.Scatter(
                x=reds,
                y=ranked["country"],
                mode="markers+text",
                name="Change (before − after)",
                marker=dict(color=marker_colors, size=12, symbol="diamond", line=dict(width=1, color="#fffaf2")),
                text=[f"{value:+.3f}" for value in reds],
                textfont=dict(size=11, color="#1f2a1f"),
                textposition="middle right",
                visible=visible,
                hovertemplate=(
                    "%{y}<br>Change: %{x:+.3f} (before − after)<br>"
                    "Positive: mortality fell; negative: rose<extra></extra>"
                ),
            ),
            row=1,
            col=2,
        )

    default_threshold = THRESHOLDS[DEFAULT_THRESHOLD_INDEX]
    buttons = []
    for idx, threshold in enumerate(THRESHOLDS):
        vis = [False] * (len(THRESHOLDS) * traces_per_threshold)
        vis[idx * traces_per_threshold] = True
        vis[idx * traces_per_threshold + 1] = True
        vis[idx * traces_per_threshold + 2] = True
        buttons.append(
            dict(
                label=f"{threshold}%",
                method="update",
                args=[
                    {"visible": vis},
                    {
                        # Flat layout keys so Plotly reliably applies title on dropdown change
                        "title.text": TITLE_TEMPLATE.format(pct=threshold),
                        "yaxis.categoryarray": panel,
                        "yaxis2.categoryarray": panel,
                    },
                ],
            )
        )

    fig.update_layout(
        title=dict(
            text=TITLE_TEMPLATE.format(pct=default_threshold),
            font=dict(size=17, color="#1f2a1f"),
            x=0.5,
            xanchor="center",
        ),
        barmode="group",
        updatemenus=[
            dict(
                buttons=buttons,
                x=1,
                xanchor="right",
                y=1.15,
                yanchor="top",
                active=DEFAULT_THRESHOLD_INDEX,
            )
        ],
        xaxis=dict(title="Average deaths per 100k", showgrid=True, gridcolor="#efe4d4"),
        xaxis2=dict(
            title="Change (before − after)",
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor="rgba(78, 95, 88, 0.35)",
            showgrid=True,
            gridcolor="rgba(239, 228, 212, 0.9)",
        ),
        yaxis=dict(autorange="reversed", categoryorder="array", categoryarray=panel),
        yaxis2=dict(autorange="reversed", showticklabels=False, categoryorder="array", categoryarray=panel),
        legend=dict(orientation="h", y=-0.18),
    )
    fig.update_xaxes(range=[x2_min, x2_max], row=1, col=2)
    fig.update_traces(width=0.34, selector=dict(type="bar"))
    write_figure(fig, "ranking-threshold.html", height=560)


if __name__ == "__main__":
    build()
