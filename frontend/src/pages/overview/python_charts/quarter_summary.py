from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from _shared import read_csv, read_group_long, sort_quarters, write_figure


AGGREGATES = {
    "World",
    "Africa",
    "Asia",
    "Europe",
    "North America",
    "South America",
    "Oceania",
    "European Union (27)",
    "European Union",
    "High-income countries",
    "Upper-middle-income countries",
    "Lower-middle-income countries",
    "Low-income countries",
    "International",
}


def _is_aggregate(country: str) -> bool:
    return country in AGGREGATES or "income" in str(country).lower()


def build() -> None:
    country = read_csv("country_quarterly_overview.csv")
    country = country.rename(columns={"location": "country"})
    country = country[~country["country"].map(_is_aggregate)].copy()
    quarters = sort_quarters(country["quarter"].dropna().astype(str).unique().tolist())
    selected_quarter = quarters[-1]

    country["vacc_rolling_12m_per_hundred"] = pd.to_numeric(country["vacc_rolling_12m_per_hundred"], errors="coerce")
    country["cases_new_cases_pm7_avg"] = pd.to_numeric(country["cases_new_cases_pm7_avg"], errors="coerce")
    groups = read_group_long()
    groups["value"] = pd.to_numeric(groups["value"], errors="coerce")

    fig = make_subplots(
        rows=2,
        cols=2,
        specs=[[{"type": "bar"}, {"type": "bar"}], [{"type": "table", "colspan": 2}, None]],
        subplot_titles=(
            "Vaccination leader ranking",
            "Case hotspot ranking",
            "Group-level snapshot",
        ),
        vertical_spacing=0.18,
        horizontal_spacing=0.14,
    )

    for quarter in quarters:
        is_selected = quarter == selected_quarter
        q_country = country[country["quarter"] == quarter].copy()
        vacc_top = q_country.nlargest(16, "vacc_rolling_12m_per_hundred")
        case_top = q_country.nlargest(16, "cases_new_cases_pm7_avg")

        q_groups = groups[(groups["quarter"] == quarter) & (groups["metric"] == "first_dose_progress")]
        group_leader = q_groups.nlargest(1, "value")
        leader = group_leader.iloc[0] if not group_leader.empty else None

        fig.add_trace(
            go.Bar(
                x=vacc_top["vacc_rolling_12m_per_hundred"],
                y=vacc_top["country"],
                orientation="h",
                marker=dict(color="#1d6b57"),
                hovertemplate="%{y}<br>12-month dose intensity: %{x:.1f} / 100<extra></extra>",
                visible=is_selected,
                name=f"{quarter} vaccination leaders",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Bar(
                x=case_top["cases_new_cases_pm7_avg"],
                y=case_top["country"],
                orientation="h",
                marker=dict(color="#b85c38"),
                hovertemplate="%{y}<br>7-day avg new cases: %{x:.0f} / 1M<extra></extra>",
                visible=is_selected,
                name=f"{quarter} case hotspots",
            ),
            row=1,
            col=2,
        )
        fig.add_trace(
            go.Table(
                header=dict(values=["Quarter", "Coverage leader", "First-dose progress"], fill_color="#f5efe4", align="left"),
                cells=dict(
                    values=[
                        [quarter],
                        [leader["group"] if leader is not None else "No data"],
                        [f"{leader['value'] * 100:.1f}%" if leader is not None else "N/A"],
                    ],
                    fill_color="#fffaf2",
                    align="left",
                ),
                visible=is_selected,
                name=f"{quarter} group snapshot",
            ),
            row=2,
            col=1,
        )

    buttons = []
    traces_per_quarter = 3
    for index, quarter in enumerate(quarters):
        visible = [False] * len(fig.data)
        start = index * traces_per_quarter
        for trace_index in range(start, start + traces_per_quarter):
            visible[trace_index] = True
        buttons.append(
            dict(
                label=quarter,
                method="update",
                args=[
                    {"visible": visible},
                    {"title.text": f"Quarterly vaccination and case situation: {quarter}"},
                ],
            )
        )

    fig.update_yaxes(autorange="reversed", row=1, col=1)
    fig.update_yaxes(autorange="reversed", row=1, col=2)
    fig.update_xaxes(title="Dose intensity / 100", row=1, col=1)
    fig.update_xaxes(title="Cases / 1M", row=1, col=2)
    fig.update_layout(
        title=dict(text=f"Quarterly vaccination and case situation: {selected_quarter}", x=0.5, xanchor="center", font=dict(size=17)),
        showlegend=False,
        updatemenus=[
            dict(
                active=len(buttons) - 1,
                buttons=buttons,
                direction="down",
                x=0,
                xanchor="left",
                y=1.11,
                yanchor="top",
                bgcolor="#fffaf2",
                bordercolor="#d7c8b5",
                borderwidth=1,
                font=dict(size=12),
            )
        ],
    )
    fig.add_annotation(
        text="Quarter",
        x=0,
        xref="paper",
        y=1.16,
        yref="paper",
        showarrow=False,
        xanchor="left",
        font=dict(size=12, color="#5e6b60"),
    )
    write_figure(fig, "overview-quarter-summary.html", height=780, margin=dict(l=132, r=42, t=112, b=52))


if __name__ == "__main__":
    build()
