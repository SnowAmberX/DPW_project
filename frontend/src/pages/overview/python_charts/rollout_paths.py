from __future__ import annotations

import plotly.graph_objects as go

from _shared import read_group_long, sort_quarters, write_figure


METRICS = [
    ("rollout_speed", "Rollout speed", "Quarterly rollout speed (/100)", lambda v: f"{v:.3f} / 100"),
    ("first_dose_progress", "First-dose progress", "People with first dose (%)", lambda v: f"{v * 100:.1f}%"),
    ("full_vaccination_progress", "Full vaccination progress", "Fully vaccinated (%)", lambda v: f"{v * 100:.1f}%"),
]

PREFERRED_GROUPS = [
    "European Union (27)",
    "High-income countries",
    "Upper-middle-income countries",
    "Lower-middle-income countries",
    "Low-income countries",
    "World",
]

PALETTE = {
    "European Union (27)": "#1d6b57",
    "Europe": "#3f8f73",
    "High-income countries": "#4f76b4",
    "Upper-middle-income countries": "#d08755",
    "Lower-middle-income countries": "#a86dbe",
    "Low-income countries": "#c9554e",
    "World": "#7b8b72",
}


def build() -> None:
    df = read_group_long()
    df["value"] = df["value"].apply(lambda v: float(v) if str(v) != "nan" else None)
    quarters = sort_quarters(df["quarter"].dropna().astype(str).unique().tolist())
    groups = [group for group in PREFERRED_GROUPS if group in set(df["group"])]
    if not groups:
        groups = sorted(df["group"].dropna().unique().tolist())[:6]

    fig = go.Figure()
    trace_counts = []
    for metric_index, (metric, _, _, formatter) in enumerate(METRICS):
        metric_traces = 0
        for group in groups:
            subset = df[(df["metric"] == metric) & (df["group"] == group) & (df["quarter"].isin(quarters))].copy()
            subset = subset.sort_values("quarter", key=lambda s: s.map(lambda q: quarters.index(q)))
            value_by_quarter = dict(zip(subset["quarter"], subset["value"]))
            y_values = [
                (value_by_quarter.get(quarter) * (100 if metric != "rollout_speed" else 1))
                if quarter in value_by_quarter
                else None
                for quarter in quarters
            ]
            custom_values = [
                formatter(value_by_quarter[quarter])
                if quarter in value_by_quarter
                else None
                for quarter in quarters
            ]
            fig.add_trace(
                go.Scatter(
                    x=quarters,
                    y=y_values,
                    mode="lines+markers",
                    name=group,
                    line=dict(width=3, color=PALETTE.get(group, "#6ea58a"), shape="linear"),
                    marker=dict(size=7, line=dict(width=1.2, color="#fffaf2")),
                    visible=metric_index == 0,
                    customdata=custom_values,
                    hovertemplate="Group: %{fullData.name}<br>Quarter: %{x}<br>Value: %{customdata}<extra></extra>",
                )
            )
            metric_traces += 1
        trace_counts.append(metric_traces)

    buttons = []
    offset = 0
    total = sum(trace_counts)
    for idx, ((metric, label, axis_label, _), count) in enumerate(zip(METRICS, trace_counts)):
        visible = [False] * total
        for trace_index in range(offset, offset + count):
            visible[trace_index] = True
        buttons.append(
            dict(
                label=label,
                method="update",
                args=[
                    {"visible": visible},
                    {"yaxis.title.text": axis_label, "title.text": "Quarterly rollout comparison"},
                ],
            )
        )
        offset += count

    fig.update_layout(
        title=dict(text="Quarterly rollout comparison", x=0.5, xanchor="center", font=dict(size=17)),
        updatemenus=[
            dict(buttons=buttons, active=0, x=1, xanchor="right", y=1.14, yanchor="top"),
        ],
        xaxis=dict(title="Quarter", categoryorder="array", categoryarray=quarters, showgrid=False),
        yaxis=dict(title=METRICS[0][2], gridcolor="rgba(31,42,31,0.09)", zeroline=False),
        legend=dict(orientation="h", y=-0.18, x=0.02),
        hovermode="x unified",
    )
    write_figure(fig, "overview-rollout-paths.html", height=590, margin=dict(t=84, b=112))


if __name__ == "__main__":
    build()
