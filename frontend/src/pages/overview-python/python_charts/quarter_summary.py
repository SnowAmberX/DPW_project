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
    q_country = country[country["quarter"] == selected_quarter].copy()

    vacc_top = q_country.nlargest(16, "vacc_rolling_12m_per_hundred")
    case_top = q_country.nlargest(16, "cases_new_cases_pm7_avg")

    groups = read_group_long()
    groups["value"] = pd.to_numeric(groups["value"], errors="coerce")
    q_groups = groups[(groups["quarter"] == selected_quarter) & (groups["metric"] == "first_dose_progress")]
    group_leader = q_groups.nlargest(1, "value")

    milestones = read_csv("group_milestone_table.csv")
    milestones = milestones[
        (milestones["metric"] == "full_vaccination_progress") & (pd.to_numeric(milestones["threshold"], errors="coerce") == 0.75)
    ].copy()
    milestones = milestones.dropna(subset=["first_quarter_reached"]).sort_values("first_quarter_reached")
    milestone_text = "Milestone table unavailable"
    if not milestones.empty:
        row = milestones.iloc[0]
        milestone_text = f"{row.get('group', row.get('country', 'Group'))}: {row['first_quarter_reached']}"

    fig = make_subplots(
        rows=2,
        cols=2,
        specs=[[{"type": "bar"}, {"type": "bar"}], [{"type": "table"}, {"type": "indicator"}]],
        subplot_titles=(
            "Vaccination leader ranking",
            "Case hotspot ranking",
            "Group-level snapshot",
            "Milestone pace",
        ),
        vertical_spacing=0.18,
        horizontal_spacing=0.14,
    )
    fig.add_trace(
        go.Bar(
            x=vacc_top["vacc_rolling_12m_per_hundred"],
            y=vacc_top["country"],
            orientation="h",
            marker=dict(color="#1d6b57"),
            hovertemplate="%{y}<br>12-month dose intensity: %{x:.1f} / 100<extra></extra>",
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
        ),
        row=1,
        col=2,
    )

    leader = group_leader.iloc[0] if not group_leader.empty else None
    fig.add_trace(
        go.Table(
            header=dict(values=["Quarter", "Coverage leader", "First-dose progress"], fill_color="#f5efe4", align="left"),
            cells=dict(
                values=[
                    [selected_quarter],
                    [leader["group"] if leader is not None else "No data"],
                    [f"{leader['value'] * 100:.1f}%" if leader is not None else "N/A"],
                ],
                fill_color="#fffaf2",
                align="left",
            ),
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Indicator(
            mode="number",
            value=75,
            number=dict(suffix="% completion", font=dict(size=34, color="#1d6b57")),
            title=dict(text=milestone_text, font=dict(size=15)),
        ),
        row=2,
        col=2,
    )

    fig.update_yaxes(autorange="reversed", row=1, col=1)
    fig.update_yaxes(autorange="reversed", row=1, col=2)
    fig.update_xaxes(title="Dose intensity / 100", row=1, col=1)
    fig.update_xaxes(title="Cases / 1M", row=1, col=2)
    fig.update_layout(
        title=dict(text=f"Quarterly vaccination and case situation: {selected_quarter}", x=0.5, xanchor="center", font=dict(size=17)),
        showlegend=False,
    )
    write_figure(fig, "overview-quarter-summary.html", height=780, margin=dict(l=132, r=42, t=86, b=52))


if __name__ == "__main__":
    build()
