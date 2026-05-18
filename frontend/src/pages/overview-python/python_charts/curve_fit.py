from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from _shared import read_csv, sort_quarters, write_figure


REPRESENTATIVE_GROUPS = [
    "Africa",
    "Asia",
    "Europe",
    "North America",
    "High-income countries",
    "Low-income countries",
]

PALETTE = ["#1d6b57", "#4f76b4", "#b85c38", "#c47b2f", "#506f97", "#875167"]


def _metric_label(metric: str) -> str:
    return "First-dose progress" if metric == "first_dose_progress" else "Full-vaccination progress"


def _axis_ref(index: int, axis: str) -> str:
    if index == 0:
        return axis
    return f"{axis}{index + 1}"


def _domain_ref(index: int, axis: str) -> str:
    return f"{_axis_ref(index, axis)} domain"


def _curve_marks(subset: pd.DataFrame, plateau_target: float) -> dict[str, object]:
    rows = subset.sort_values("t").reset_index(drop=True)
    if rows.empty:
        return {
            "peak": None,
            "rapid_start": None,
            "rapid_end": None,
            "plateau": None,
        }

    deltas = []
    for index in range(1, len(rows)):
        delta = rows.loc[index, "yhat"] - rows.loc[index - 1, "yhat"]
        deltas.append((index, delta))

    peak = None
    rapid_start = None
    rapid_end = None
    if deltas:
        peak_index, peak_delta = max(deltas, key=lambda item: item[1])
        peak = rows.loc[peak_index]
        threshold = peak_delta * 0.8
        rapid_indices = [idx for idx, delta in deltas if delta >= threshold]
        if rapid_indices:
            rapid_start = rows.loc[rapid_indices[0]]
            rapid_end = rows.loc[rapid_indices[-1]]

    plateau_rows = rows[rows["yhat"] >= plateau_target]
    plateau = plateau_rows.iloc[0] if not plateau_rows.empty else None
    return {
        "peak": peak,
        "rapid_start": rapid_start,
        "rapid_end": rapid_end,
        "plateau": plateau,
    }


def _visible_mark(mark: object, frame_index: int) -> bool:
    if mark is None:
        return False
    return int(mark["t"]) <= frame_index


def _mark_trace(mark: object, frame_index: int, label: str, color: str) -> go.Scatter:
    if _visible_mark(mark, frame_index):
        return go.Scatter(
            x=[mark["quarter"]],
            y=[mark["yhat"] * 100],
            mode="markers",
            name=label,
            marker=dict(size=11, color=color, line=dict(width=2, color="#fffaf2")),
            legendgroup=label,
            showlegend=False,
            hovertemplate=f"{label}<br>Quarter: %{{x}}<br>Fitted: %{{y:.1f}}%<extra></extra>",
        )
    return go.Scatter(x=[], y=[], mode="markers", name=label, showlegend=False)


def _guide_trace(mark: object, frame_index: int, label: str, color: str) -> go.Scatter:
    if _visible_mark(mark, frame_index):
        return go.Scatter(
            x=[mark["quarter"], mark["quarter"]],
            y=[0, 105],
            mode="lines",
            name=label,
            line=dict(color=color, width=1.8, dash="dot"),
            legendgroup=label,
            showlegend=False,
            hovertemplate=f"{label}<br>Quarter: %{{x}}<extra></extra>",
        )
    return go.Scatter(x=[], y=[], mode="lines", name=label, showlegend=False)


def build() -> None:
    summary = read_csv("group_curve_fit_summary.csv").rename(columns={"country": "group"})
    values = read_csv("group_curve_fit_values.csv").rename(columns={"country": "group"})
    summary["best_model"] = summary["best_model"].str.lower()
    summary["r2"] = pd.to_numeric(summary["r2"], errors="coerce")
    values["yhat"] = pd.to_numeric(values["yhat"], errors="coerce")
    values["t"] = pd.to_numeric(values["t"], errors="coerce").astype("Int64")

    fig = make_subplots(
        rows=2,
        cols=3,
        shared_yaxes=True,
        subplot_titles=REPRESENTATIVE_GROUPS,
        vertical_spacing=0.18,
        horizontal_spacing=0.08,
    )

    metric = "first_dose_progress"
    quarters = sort_quarters(values["quarter"].dropna().astype(str).unique().tolist())
    final_frame_index = max(len(quarters) - 1, 0)
    model_notes = []
    for index, group in enumerate(REPRESENTATIVE_GROUPS):
        row = index // 3 + 1
        col = index % 3 + 1
        summary_row = summary[(summary["group"] == group) & (summary["metric"] == metric)]
        if summary_row.empty:
            continue
        model = summary_row.iloc[0]["best_model"]
        subset = values[
            (values["group"] == group)
            & (values["metric"] == metric)
            & (values["model"].str.lower() == model)
            & (values["quarter"].isin(quarters))
        ].copy()
        subset = subset.sort_values("quarter", key=lambda s: s.map(lambda q: quarters.index(q)))
        subset[metric] = pd.to_numeric(subset[metric], errors="coerce")
        color = PALETTE[index % len(PALETTE)]
        plateau_target = float(summary_row.iloc[0]["param_1"]) * 0.95 if pd.notna(summary_row.iloc[0]["param_1"]) else 0.95
        marks = _curve_marks(subset, plateau_target)
        visible_subset = subset[subset["t"] <= final_frame_index]
        observed = visible_subset[metric] * 100
        fitted = visible_subset["yhat"] * 100
        fig.add_trace(
            go.Scatter(
                x=visible_subset["quarter"],
                y=observed,
                mode="lines+markers",
                name="Observed" if index == 0 else "",
                line=dict(color="rgba(31,42,31,0.48)", width=2.2, dash="dash", shape="spline", smoothing=0.5),
                marker=dict(size=6.5, color="#fffaf2", line=dict(width=1.7, color="rgba(31,42,31,0.62)")),
                legendgroup="observed",
                showlegend=index == 0,
                hovertemplate=group + "<br>%{x}<br>Observed: %{y:.1f}%<extra></extra>",
            ),
            row=row,
            col=col,
        )
        fig.add_trace(
            go.Scatter(
                x=visible_subset["quarter"],
                y=fitted,
                mode="lines",
                name="Fitted" if index == 0 else "",
                line=dict(color=color, width=3, shape="spline", smoothing=0.55),
                legendgroup="fitted",
                showlegend=index == 0,
                hovertemplate=group + "<br>%{x}<br>Fitted: %{y:.1f}%<extra></extra>",
            ),
            row=row,
            col=col,
        )
        peak_trace = _mark_trace(marks["peak"], final_frame_index, "Highest growth", "#d1493f")
        peak_trace.showlegend = index == 0
        fig.add_trace(peak_trace, row=row, col=col)

        rapid_start_trace = _mark_trace(marks["rapid_start"], final_frame_index, "Rapid-growth start", "#2e8b57")
        rapid_start_trace.showlegend = index == 0
        fig.add_trace(rapid_start_trace, row=row, col=col)

        rapid_end_trace = _mark_trace(marks["rapid_end"], final_frame_index, "Rapid-growth end", "#4aa96c")
        rapid_end_trace.showlegend = index == 0
        fig.add_trace(rapid_end_trace, row=row, col=col)

        plateau_trace = _guide_trace(marks["plateau"], final_frame_index, "95% plateau entry", "#1d6b57")
        plateau_trace.showlegend = index == 0
        fig.add_trace(plateau_trace, row=row, col=col)

        model_notes.append(f"<b>{group}</b>: {model.title()} R2 {summary_row.iloc[0]['r2']:.3f}")

    fig.update_yaxes(range=[0, 105], ticksuffix="%")
    fig.update_xaxes(tickangle=-30)
    for note_index, note in enumerate(model_notes):
        note_row = note_index // 3
        note_col = note_index % 3
        fig.add_annotation(
            x=0.17 + note_col * 0.33,
            y=-0.17 - note_row * 0.055,
            xref="paper",
            yref="paper",
            text=note,
            showarrow=False,
            align="center",
            font=dict(size=11, color="#5e6b60"),
        )

    fig.update_layout(
        title=dict(text=f"Observed vs fitted rollout trajectories: {_metric_label(metric)}", x=0.5, xanchor="center", font=dict(size=17)),
        legend=dict(
            orientation="h",
            x=0.5,
            xanchor="center",
            y=-0.08,
            yanchor="top",
            bgcolor="rgba(255,250,242,0)",
            font=dict(size=11),
        ),
    )
    write_figure(fig, "overview-curve-fit.html", height=760, margin=dict(t=84, b=178))

    summary_table = summary.copy()
    summary_table["Metric"] = summary_table["metric"].map(_metric_label)
    summary_table["R2"] = summary_table["r2"].map(lambda v: f"{v:.3f}" if pd.notna(v) else "N/A")
    summary_table["RMSE"] = pd.to_numeric(summary_table["rmse"], errors="coerce").map(lambda v: f"{v:.3f}" if pd.notna(v) else "N/A")
    table_rows = summary_table[summary_table["metric"] == "first_dose_progress"].sort_values("group")
    table_fig = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=["Group", "Metric", "Best model", "R2", "RMSE"],
                    fill_color="#f5efe4",
                    align="left",
                    font=dict(color="#304238", size=12),
                ),
                cells=dict(
                    values=[
                        table_rows["group"],
                        table_rows["Metric"],
                        table_rows["best_model"].str.title(),
                        table_rows["R2"],
                        table_rows["RMSE"],
                    ],
                    fill_color="#fffaf2",
                    align="left",
                    height=28,
                    font=dict(color="#5e6b60", size=12),
                ),
            )
        ]
    )
    table_fig.update_layout(title=dict(text="Curve-fit Summary Panel", x=0.5, xanchor="center", font=dict(size=17)))
    write_figure(table_fig, "overview-curve-summary.html", height=560, margin=dict(l=24, r=24, t=72, b=24))


if __name__ == "__main__":
    build()
