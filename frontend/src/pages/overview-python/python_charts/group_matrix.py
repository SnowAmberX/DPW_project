from __future__ import annotations

import plotly.graph_objects as go

from _shared import group_order, read_group_long, sort_quarters, write_figure


METRICS = [
    ("first_dose_progress", "First-dose progress", [[0, "#edf5f1"], [0.45, "#9fcdbd"], [1, "#1d6b57"]]),
    ("full_vaccination_progress", "Full vaccination progress", [[0, "#edf5f1"], [0.45, "#9fcdbd"], [1, "#1d6b57"]]),
]


def build() -> None:
    df = read_group_long()
    df["value"] = df["value"].astype(float)
    quarters = sort_quarters(df["quarter"].dropna().astype(str).unique().tolist())
    order = group_order()
    groups = sorted(
        df["group"].dropna().unique().tolist(),
        key=lambda g: (order.get(g, 999), str(g).lower()),
    )

    fig = go.Figure()
    for idx, (metric, label, scale) in enumerate(METRICS):
        pivot = (
            df[(df["metric"] == metric) & (df["quarter"].isin(quarters))]
            .pivot_table(index="group", columns="quarter", values="value", aggfunc="mean")
            .reindex(index=groups, columns=quarters)
        )
        fig.add_trace(
            go.Heatmap(
                z=pivot.values * 100,
                x=quarters,
                y=groups,
                visible=idx == 0,
                colorscale=scale,
                xgap=6,
                ygap=6,
                colorbar=dict(title=label, ticksuffix="%", thickness=14, len=0.78),
                hovertemplate="Group: %{y}<br>Quarter: %{x}<br>" + label + ": %{z:.1f}%<extra></extra>",
            )
        )

    buttons = []
    for idx, (_, label, _) in enumerate(METRICS):
        visible = [False] * len(METRICS)
        visible[idx] = True
        buttons.append(dict(label=label, method="update", args=[{"visible": visible}]))

    fig.update_layout(
        title=dict(text="Cross-group Quarterly Vaccination Matrix", x=0.5, xanchor="center", font=dict(size=17)),
        updatemenus=[dict(buttons=buttons, active=0, x=1, xanchor="right", y=1.12, yanchor="top")],
        xaxis=dict(title="Quarter", tickangle=-30, showgrid=False),
        yaxis=dict(title="", autorange="reversed", showgrid=False),
    )
    write_figure(fig, "overview-group-matrix.html", height=620, margin=dict(l=176, t=82, b=76))


if __name__ == "__main__":
    build()
