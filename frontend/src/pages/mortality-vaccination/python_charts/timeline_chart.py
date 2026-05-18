from __future__ import annotations

import plotly.graph_objects as go

from _shared import TIMELINE_MONTH_END, monthly_compact, write_figure

TIMELINE_TITLE_TEMPLATE = "Country Vaccination Rollout and Mortality Trend: {country}"

# Tier-2 dropdown rows: continental / macro aggregates (alphabetical among themselves).
_CONTINENT_TIER = frozenset(
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

_INCOME_LABELS = frozenset(
    {
        "High-income countries",
        "Low-income countries",
        "Lower-middle-income countries",
        "Upper-middle-income countries",
    }
)


def _timeline_dropdown_sort_key(name: str) -> tuple[int, str]:
    """World → continents (A–Z) → income groups (A–Z) → countries (A–Z)."""
    lowered = name.lower()
    if name == "World":
        return (0, lowered)
    if name in _CONTINENT_TIER:
        return (1, lowered)
    if name in _INCOME_LABELS:
        return (2, lowered)
    return (3, lowered)


_TIMELINE_EXCLUDE_COUNTRIES = frozenset({"China"})


def build() -> None:
    df = monthly_compact()
    df = df[df["month"] <= TIMELINE_MONTH_END].copy()
    raw_names = df.groupby("country")["population"].max().sort_index().index.tolist()
    raw_names = [c for c in raw_names if c not in _TIMELINE_EXCLUDE_COUNTRIES]
    countries = sorted(raw_names, key=_timeline_dropdown_sort_key)

    fig = go.Figure()
    buttons = []
    trace_count_per_country = 4

    for idx, country in enumerate(countries):
        subset = df[df["country"] == country].sort_values("month")
        visible = idx == 0
        last_row = subset.iloc[-1]

        fig.add_trace(
            go.Scatter(
                x=subset["month"],
                y=subset["deaths_per_100k"],
                mode="lines",
                name="Deaths per 100k",
                line=dict(color="#b85c38", width=3.2, shape="spline", smoothing=0.65),
                hovertemplate="Month: %{x}<br>Deaths/100k: %{y:.3f}<extra></extra>",
                visible=visible,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[last_row["month"]],
                y=[last_row["deaths_per_100k"]],
                mode="markers+text",
                marker=dict(size=9, color="#b85c38", line=dict(width=1.4, color="#fffaf2")),
                text=["Deaths"],
                textposition="top center",
                textfont=dict(size=11, color="#8d452a"),
                hoverinfo="skip",
                showlegend=False,
                visible=visible,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=subset["month"],
                y=subset["vaccinated_pct"],
                mode="lines",
                name="Vaccinated population %",
                line=dict(color="#1d6b57", width=3.2, shape="spline", smoothing=0.65),
                yaxis="y2",
                hovertemplate="Month: %{x}<br>Vaccinated: %{y:.1f}%<extra></extra>",
                visible=visible,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[last_row["month"]],
                y=[last_row["vaccinated_pct"]],
                mode="markers+text",
                marker=dict(size=9, color="#1d6b57", line=dict(width=1.4, color="#fffaf2")),
                text=["Coverage"],
                textposition="bottom center",
                textfont=dict(size=11, color="#1d6b57"),
                yaxis="y2",
                hoverinfo="skip",
                showlegend=False,
                visible=visible,
            )
        )

        visibility = [False] * (len(countries) * trace_count_per_country)
        start = idx * trace_count_per_country
        visibility[start : start + trace_count_per_country] = [True, True, True, True]
        buttons.append(
            dict(
                label=country,
                method="update",
                args=[
                    {"visible": visibility},
                    {
                        "title.text": TIMELINE_TITLE_TEMPLATE.format(country=country),
                        "annotations[0].text": f"Showing {country}",
                    },
                ],
            )
        )

    initial_country = countries[0]
    fig.update_layout(
        title=dict(
            text=TIMELINE_TITLE_TEMPLATE.format(country=initial_country),
            font=dict(size=17, color="#1f2a1f"),
            x=0.5,
            xanchor="center",
        ),
        updatemenus=[
            dict(
                type="dropdown",
                buttons=buttons,
                direction="down",
                showactive=True,
                x=1,
                xanchor="right",
                y=1.16,
                yanchor="top",
                active=0,
                bgcolor="rgba(255,250,242,0.96)",
                bordercolor="rgba(29, 107, 87, 0.24)",
                borderwidth=1,
                pad=dict(t=4, r=4, b=4, l=4),
            )
        ],
        hovermode="x unified",
        yaxis=dict(
            title="Deaths per 100k",
            showgrid=True,
            gridcolor="rgba(78, 95, 88, 0.10)",
            zeroline=False,
        ),
        yaxis2=dict(
            title="Vaccinated population %",
            overlaying="y",
            side="right",
            range=[0, 100],
            showgrid=False,
            zeroline=False,
        ),
        xaxis=dict(showgrid=False),
        legend=dict(orientation="h", y=-0.08, x=0.02),
        annotations=[
            dict(
                x=0.99,
                y=1.12,
                xref="paper",
                yref="paper",
                xanchor="right",
                yanchor="top",
                showarrow=False,
                text=f"Showing {initial_country}",
                font=dict(size=12, color="#5e6b60"),
            )
        ],
    )
    write_figure(
        fig,
        "timeline-country.html",
        height=560,
        margin=dict(l=58, r=58, t=82, b=48),
        overscroll_contain=True,
    )


if __name__ == "__main__":
    build()
