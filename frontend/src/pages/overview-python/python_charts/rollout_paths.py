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
    final_frame_index = max(len(quarters) - 1, 0)
    groups = [group for group in PREFERRED_GROUPS if group in set(df["group"])]
    if not groups:
        groups = sorted(df["group"].dropna().unique().tolist())[:6]

    fig = go.Figure()
    trace_counts = []
    trace_payloads = []
    for metric_index, (metric, _, _, formatter) in enumerate(METRICS):
        metric_traces = 0
        for group in groups:
            subset = df[(df["metric"] == metric) & (df["group"] == group) & (df["quarter"].isin(quarters))].copy()
            subset = subset.sort_values("quarter", key=lambda s: s.map(lambda q: quarters.index(q)))
            subset["frame_index"] = subset["quarter"].map(lambda q: quarters.index(q))
            visible_subset = subset[subset["frame_index"] <= final_frame_index]
            y_values = visible_subset["value"] * (100 if metric != "rollout_speed" else 1)
            fig.add_trace(
                go.Scatter(
                    x=visible_subset["quarter"],
                    y=y_values,
                    mode="lines+markers",
                    name=group,
                    line=dict(width=3, color=PALETTE.get(group, "#6ea58a"), shape="spline", smoothing=0.55),
                    marker=dict(size=7, line=dict(width=1.2, color="#fffaf2")),
                    visible=metric_index == 0,
                    customdata=visible_subset["value"].map(formatter),
                    hovertemplate="Group: %{fullData.name}<br>Quarter: %{x}<br>Value: %{customdata}<extra></extra>",
                )
            )
            trace_payloads.append(
                {
                    "metric": metric,
                    "group": group,
                    "subset": subset,
                    "scale": 100 if metric != "rollout_speed" else 1,
                    "formatter": formatter,
                }
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

    frames = []
    for frame_index, quarter in enumerate(quarters):
        frame_traces = []
        for payload in trace_payloads:
            visible_subset = payload["subset"][payload["subset"]["frame_index"] <= frame_index]
            frame_traces.append(
                go.Scatter(
                    x=visible_subset["quarter"],
                    y=visible_subset["value"] * payload["scale"],
                    customdata=visible_subset["value"].map(payload["formatter"]),
                )
            )
        frames.append(go.Frame(name=quarter, data=frame_traces))
    fig.frames = frames

    fig.update_layout(
        title=dict(text="Quarterly rollout comparison", x=0.5, xanchor="center", font=dict(size=17)),
        updatemenus=[
            dict(buttons=buttons, active=0, x=1, xanchor="right", y=1.14, yanchor="top"),
            dict(
                type="buttons",
                direction="left",
                x=0.02,
                y=-0.1,
                xanchor="left",
                yanchor="top",
                buttons=[
                    dict(
                        label="Play",
                        method="animate",
                        args=[
                            None,
                            {
                                "frame": {"duration": 650, "redraw": True},
                                "transition": {"duration": 240, "easing": "cubic-in-out"},
                                "fromcurrent": True,
                            },
                        ],
                    ),
                    dict(
                        label="Pause",
                        method="animate",
                        args=[[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}],
                    ),
                ],
            ),
        ],
        sliders=[
            dict(
                active=final_frame_index,
                x=0.18,
                y=-0.1,
                len=0.78,
                currentvalue=dict(prefix="Quarter: ", font=dict(size=12, color="#5e6b60")),
                pad=dict(t=18, b=0),
                steps=[
                    dict(
                        label=quarter,
                        method="animate",
                        args=[
                            [quarter],
                            {
                                "mode": "immediate",
                                "frame": {"duration": 220, "redraw": True},
                                "transition": {"duration": 160},
                            },
                        ],
                    )
                    for quarter in quarters
                ],
            )
        ],
        xaxis=dict(title="Quarter", categoryorder="array", categoryarray=quarters, showgrid=False),
        yaxis=dict(title=METRICS[0][2], gridcolor="rgba(31,42,31,0.09)", zeroline=False),
        legend=dict(orientation="h", y=-0.21, x=0.02),
        hovermode="x unified",
    )
    write_figure(fig, "overview-rollout-paths.html", height=630, margin=dict(t=84, b=150))


if __name__ == "__main__":
    build()
