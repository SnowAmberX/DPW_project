"""
Exploratory statistics tables for the mortality page (undergraduate-style summary).
Outputs a single Plotly HTML with three stacked tables: descriptive stats, Spearman
correlations, and pooled OLS (coefficients + fit summary in one block).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from _shared import OUTPUT_DIR, ROOT, TIMELINE_MONTH_END, monthly_compact, write_figure

# Country-only panel (no World): pooled stats would double-count if a global aggregate were
# mixed with country rows. Names must exist in monthly_compact() for this build.
ANALYSIS_COUNTRIES = [
    "Mexico",
    "United States",
    "Germany",
    "Japan",
    "Brazil",
    "India",
]


def _descriptive_table(df: pd.DataFrame, countries: list[str]) -> go.Table:
    rows_data = []
    for country in countries:
        s = df[df["country"] == country]
        n = int(len(s))
        if n == 0:
            continue
        rows_data.append(
            {
                "Entity": country,
                "Months": n,
                "Deaths/100k μ": s["deaths_per_100k"].mean(),
                "Deaths/100k σ": s["deaths_per_100k"].std(ddof=0),
                "Vaccinated % μ": s["vaccinated_pct"].mean(),
                "Cases/100k μ": s["cases_per_100k"].mean(),
            }
        )
    tdf = pd.DataFrame(rows_data)
    return go.Table(
        header=dict(
            values=list(tdf.columns),
            fill_color="rgba(29, 107, 87, 0.18)",
            font=dict(size=12, color="#1f2a1f"),
            align="left",
        ),
        cells=dict(
            values=[tdf[c].tolist() for c in tdf.columns],
            format=[None, None, ".4f", ".4f", ".2f", ".2f"],
            align="left",
            font=dict(size=11, color="#1f2a1f"),
            fill_color="rgba(255, 250, 242, 0.96)",
        ),
    )


def _spearman_table(pooled: pd.DataFrame) -> go.Table:
    cols = ["deaths_per_100k", "vaccinated_pct", "cases_per_100k"]
    rho = pooled[cols].corr(method="spearman")
    # Present as long-form pairs relevant for storytelling
    pairs = [
        ("deaths_per_100k", "vaccinated_pct", "Deaths/100k vs vaccinated %"),
        ("deaths_per_100k", "cases_per_100k", "Deaths/100k vs cases/100k"),
        ("vaccinated_pct", "cases_per_100k", "Vaccinated % vs cases/100k"),
    ]
    labels = []
    coeffs = []
    for a, b, lab in pairs:
        labels.append(lab)
        coeffs.append(float(rho.loc[a, b]))
    n = len(pooled)
    summary = pd.DataFrame(
        {
            "Pair": labels,
            "Spearman ρ": coeffs,
            "Pooled months": [n, n, n],
        }
    )
    return go.Table(
        header=dict(
            values=list(summary.columns),
            fill_color="rgba(29, 107, 87, 0.18)",
            font=dict(size=12, color="#1f2a1f"),
            align="left",
        ),
        cells=dict(
            values=[summary[c].tolist() for c in summary.columns],
            format=[None, ".3f", None],
            align="left",
            font=dict(size=11, color="#1f2a1f"),
            fill_color="rgba(255, 250, 242, 0.96)",
        ),
    )


def _ols_table(pooled: pd.DataFrame, countries: list[str]) -> go.Table:
    """Pooled OLS: deaths_per_100k ~ 1 + vaccinated_pct + cases_per_100k; coefficients + fit summary in one table."""
    y = pooled["deaths_per_100k"].astype(float).to_numpy()
    v = pooled["vaccinated_pct"].astype(float).to_numpy()
    c = pooled["cases_per_100k"].astype(float).to_numpy()
    X = np.column_stack([np.ones(len(y)), v, c])
    coef, *_rest = np.linalg.lstsq(X, y, rcond=None)
    y_hat = X @ coef
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    n = len(y)
    p = X.shape[1]
    mse = ss_res / max(n - p, 1)
    coef_rows = pd.DataFrame(
        {
            "Term": ["Intercept", "Vaccinated %", "Cases/100k"],
            "Coefficient": [f"{x:.6f}" for x in coef.tolist()],
        }
    )
    summary_rows = pd.DataFrame(
        {
            "Term": ["R²", "Residual MSE", "N (country-months)", "Panel"],
            "Coefficient": [f"{r2:.4f}", f"{mse:.6f}", str(n), ", ".join(countries)],
        }
    )
    out = pd.concat([coef_rows, summary_rows], ignore_index=True)
    return go.Table(
        header=dict(
            values=list(out.columns),
            fill_color="rgba(29, 107, 87, 0.18)",
            font=dict(size=12, color="#1f2a1f"),
            align="left",
        ),
        cells=dict(
            values=[out[c].tolist() for c in out.columns],
            align="left",
            font=dict(size=11, color="#1f2a1f"),
            fill_color="rgba(255, 250, 242, 0.96)",
        ),
    )


def build() -> None:
    df = monthly_compact()
    df = df[df["month"] <= TIMELINE_MONTH_END].copy()
    present = [c for c in ANALYSIS_COUNTRIES if c in set(df["country"].unique())]
    if not present:
        raise RuntimeError("No analysis countries found in monthly_compact().")
    df = df[df["country"].isin(present)].copy()
    pooled = df.dropna(subset=["deaths_per_100k", "vaccinated_pct", "cases_per_100k"])

    t1 = _descriptive_table(df, present)
    t2 = _spearman_table(pooled)
    t3 = _ols_table(pooled, present)

    fig = make_subplots(
        rows=3,
        cols=1,
        row_heights=[0.28, 0.14, 0.54],
        vertical_spacing=0.012,
        specs=[[{"type": "table"}], [{"type": "table"}], [{"type": "table"}]],
    )
    fig.add_trace(t1, row=1, col=1)
    fig.add_trace(t2, row=2, col=1)
    fig.add_trace(t3, row=3, col=1)

    _H = 620
    fig.update_layout(
        title=dict(
            text=(
                "Statistical Summary "
                f"(monthly through {TIMELINE_MONTH_END})"
            ),
            font=dict(size=16, color="#1f2a1f"),
            x=0.5,
            xanchor="center",
        ),
        margin=dict(l=36, r=36, t=52, b=46),
        height=_H,
    )
    _m = dict(l=36, r=36, t=52, b=46)
    write_figure(fig, "mortality-stats-tables.html", height=_H, margin=_m)
    _inject_no_page_scroll("mortality-stats-tables.html")


def _inject_no_page_scroll(filename: str) -> None:
    """Suppress inner document scrollbars in the embedded Plotly page (height matches layout)."""
    inj = "<style>html,body{overflow:hidden!important;margin:0;}</style>"
    for base in (OUTPUT_DIR, ROOT / "dist" / "python-viz"):
        p = base / filename
        if p.is_file():
            html = p.read_text(encoding="utf-8")
            if "html,body{overflow:hidden!important" in html:
                continue
            if "</head>" in html:
                html = html.replace("</head>", inj + "</head>", 1)
            else:
                html = inj + html
            p.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    build()
