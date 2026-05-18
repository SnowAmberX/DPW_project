from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from _shared import TIMELINE_MONTH_END, monthly_compact, write_figure


SIZE_MIN = 16
SIZE_MAX = 58


def build_label_positions(frame_df: pd.DataFrame) -> pd.DataFrame:
    # Offset patterns cycle by sorted row order to separate labels (12 countries in panel).
    positions = [
        (3.2, 0.05),
        (-4.0, 0.07),
        (3.5, -0.045),
        (-4.2, -0.06),
        (2.8, 0.1),
        (-2.5, 0.08),
        (4.0, 0.02),
        (-3.5, -0.05),
        (2.0, -0.08),
        (-5.0, 0.03),
        (3.0, 0.12),
        (-2.0, -0.07),
        (5.0, -0.03),
    ]
    frame_df = frame_df.sort_values(["vaccinated_pct", "deaths_per_100k"]).copy()
    frame_df["label_x"] = frame_df["vaccinated_pct"]
    frame_df["label_y"] = frame_df["deaths_per_100k"]
    for idx, row_index in enumerate(frame_df.index):
        dx, dy = positions[idx % len(positions)]
        frame_df.at[row_index, "label_x"] = max(0, min(100, frame_df.at[row_index, "vaccinated_pct"] + dx))
        frame_df.at[row_index, "label_y"] = max(0.01, frame_df.at[row_index, "deaths_per_100k"] + dy)
    return frame_df


def build() -> None:
    df = monthly_compact()
    selected_countries = [
        "United States",
        "Japan",
        "Brazil",
        "Germany",
        "India",
        "Mexico",
        "Indonesia",
        "Turkey",
        "Pakistan",
        "Bangladesh",
        "Russia",
        "Vietnam",
    ]
    df = df[df["country"].isin(selected_countries)].copy()
    valid_months = (
        df.groupby("month")["vaccinated_pct"]
        .apply(lambda series: int((series > 1).sum()))
        .loc[lambda series: series >= 2]
        .index.tolist()
    )
    valid_months = [month for month in valid_months if month <= TIMELINE_MONTH_END]
    df = df[df["month"].isin(valid_months)].copy().sort_values(["month", "country"])
    df["month_label"] = df["month"]
    df["bubble_size"] = (df["cases_per_100k"].pow(0.72) * 3.4).clip(lower=SIZE_MIN, upper=SIZE_MAX)

    months = sorted(df["month_label"].unique().tolist())
    frame_map = {month: df[df["month_label"] == month].copy() for month in months}
    label_map = {month: build_label_positions(frame_map[month].copy()) for month in months}
    initial_month = months[0]
    initial = frame_map[initial_month]
    initial_labels = label_map[initial_month]

    cmax = max(df["deaths_per_100k"].max(), 0.01)
    sizeref = 2.0 * df["bubble_size"].max() / (54.0**2)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=initial["vaccinated_pct"],
            y=initial["deaths_per_100k"],
            mode="markers",
            marker=dict(
                size=initial["bubble_size"],
                sizemode="area",
                sizeref=sizeref,
                color=initial["deaths_per_100k"],
                colorscale=[[0, "#f6dfcf"], [0.45, "#c8794d"], [1, "#7b2f16"]],
                cmin=0,
                cmax=cmax,
                opacity=0.84,
                line=dict(width=1.4, color="rgba(255, 250, 242, 0.95)"),
                colorbar=dict(
                    title="Mortality level",
                    thickness=14,
                    len=0.72,
                    bgcolor="rgba(255,250,242,0.92)",
                ),
            ),
            customdata=initial[["country", "month_label", "vaccinated_pct", "deaths_per_100k", "cases_per_100k"]],
            hovertemplate=(
                "Country: %{customdata[0]}<br>"
                "Month: %{customdata[1]}<br>"
                "Vaccinated: %{customdata[2]:.1f}%<br>"
                "Deaths/100k: %{customdata[3]:.3f}<br>"
                "Cases/100k: %{customdata[4]:.2f}<extra></extra>"
            ),
            showlegend=False,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=initial_labels["label_x"],
            y=initial_labels["label_y"],
            mode="text",
            text=initial_labels["country"],
            textfont=dict(size=12, color="#45564e"),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    frames = []
    for month in months:
        frame_rows = frame_map[month]
        frame_labels = label_map[month]
        frame_traces = [
            go.Scatter(
                x=frame_rows["vaccinated_pct"],
                y=frame_rows["deaths_per_100k"],
                mode="markers",
                marker=dict(
                    size=frame_rows["bubble_size"],
                    sizemode="area",
                    sizeref=sizeref,
                    color=frame_rows["deaths_per_100k"],
                    colorscale=[[0, "#f6dfcf"], [0.45, "#c8794d"], [1, "#7b2f16"]],
                    cmin=0,
                    cmax=cmax,
                    opacity=0.84,
                    line=dict(width=1.4, color="rgba(255, 250, 242, 0.95)"),
                ),
                customdata=frame_rows[["country", "month_label", "vaccinated_pct", "deaths_per_100k", "cases_per_100k"]],
                hovertemplate=(
                    "Country: %{customdata[0]}<br>"
                    "Month: %{customdata[1]}<br>"
                    "Vaccinated: %{customdata[2]:.1f}%<br>"
                    "Deaths/100k: %{customdata[3]:.3f}<br>"
                    "Cases/100k: %{customdata[4]:.2f}<extra></extra>"
                ),
                showlegend=False,
            ),
            go.Scatter(
                x=frame_labels["label_x"],
                y=frame_labels["label_y"],
                mode="text",
                text=frame_labels["country"],
                textfont=dict(size=12, color="#45564e"),
                hoverinfo="skip",
                showlegend=False,
            ),
        ]
        frames.append(go.Frame(name=month, data=frame_traces))

    fig.frames = frames

    fig.update_layout(
        autosize=True,
        title=dict(text="Vaccination Coverage vs Daily Mortality", font=dict(size=18)),
        xaxis=dict(
            range=[0, 100],
            tickfont=dict(size=13),
            title=dict(text="Vaccination coverage (%)", font=dict(size=14)),
            showgrid=True,
            gridcolor="rgba(78, 95, 88, 0.10)",
            zeroline=False,
        ),
        yaxis=dict(
            range=[0, max(0.05, df["deaths_per_100k"].max() * 1.1)],
            tickfont=dict(size=13),
            title=dict(text="Daily deaths per 100k", font=dict(size=14)),
            showgrid=True,
            gridcolor="rgba(78, 95, 88, 0.10)",
            zeroline=False,
        ),
        hovermode="closest",
        updatemenus=[
            {
                "type": "buttons",
                "showactive": False,
                "x": 0.02,
                "y": -0.02,
                "xanchor": "left",
                "yanchor": "top",
                "direction": "right",
                "bgcolor": "rgba(255, 250, 242, 0.96)",
                "bordercolor": "rgba(29, 107, 87, 0.28)",
                "borderwidth": 1,
                "pad": {"t": 4, "r": 4, "b": 4, "l": 4},
                "buttons": [
                    {
                        "label": "Play",
                        "method": "animate",
                        "args": [
                            None,
                            {
                                "frame": {"duration": 720, "redraw": True},
                                "transition": {"duration": 520, "easing": "cubic-in-out"},
                                "fromcurrent": True,
                            },
                        ],
                    },
                    {
                        "label": "Stop",
                        "method": "animate",
                        "args": [
                            [None],
                            {
                                "frame": {"duration": 0, "redraw": False},
                                "transition": {"duration": 0},
                                "mode": "immediate",
                            },
                        ],
                    },
                ],
            }
        ],
        sliders=[
            {
                "active": 0,
                "len": 0.93,
                "x": 0.03,
                "y": -0.16,
                "xanchor": "left",
                "yanchor": "top",
                "pad": {"t": 4, "b": 16, "l": 6, "r": 6},
                "font": {"size": 13, "color": "#45564e"},
                "currentvalue": {
                    "prefix": "Month: ",
                    "visible": True,
                    "xanchor": "left",
                    "offset": 6,
                    "font": {"size": 14, "color": "#1f2a1f"},
                },
                "steps": [
                    {
                        "label": month,
                        "method": "animate",
                        "args": [
                            [month],
                            {
                                "mode": "immediate",
                                "frame": {"duration": 0, "redraw": True},
                                "transition": {"duration": 320, "easing": "cubic-in-out"},
                            },
                        ],
                    }
                    for month in months
                ],
            }
        ],
        annotations=[],
    )

    write_figure(fig, "scatter-correlation.html", height=650, margin=dict(l=62, r=40, t=78, b=210))


if __name__ == "__main__":
    build()
