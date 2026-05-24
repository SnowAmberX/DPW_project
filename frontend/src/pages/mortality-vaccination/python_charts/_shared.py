from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd


def _find_project_root() -> Path:
    current = Path(__file__).resolve().parent
    for candidate in [current, *current.parents]:
        if (candidate / "data").exists() and (candidate / "public").exists():
            return candidate
    raise RuntimeError("Unable to locate project root containing data/ and public/")


ROOT = _find_project_root()
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "public" / "mortality-vaccination"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Inclusive month string (YYYY-MM) for timeline views; later periods are trimmed for consistency.
TIMELINE_MONTH_END = "2023-12"


def load_compact() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "cleaned_compact.txt")
    numeric_cols = [
        "new_cases",
        "population",
        "total_vaccinations",
        "people_vaccinated",
        "new_deaths",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["date"] = pd.to_datetime(df["date"])
    df = df[(df["population"] > 0) & df["country"].notna()].copy()
    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["vaccinated_pct"] = df["people_vaccinated"] / df["population"] * 100
    df["deaths_per_100k"] = df["new_deaths"] / df["population"] * 100000
    df["cases_per_100k"] = df["new_cases"] / df["population"] * 100000
    return df


def monthly_compact() -> pd.DataFrame:
    df = load_compact()
    grouped = (
        df.groupby(["country", "month"], as_index=False)
        .agg(
            vaccinated_pct=("vaccinated_pct", "mean"),
            deaths_per_100k=("deaths_per_100k", "mean"),
            cases_per_100k=("cases_per_100k", "mean"),
            population=("population", "max"),
        )
        .sort_values(["month", "country"])
    )

    country_max = grouped.groupby("country")["vaccinated_pct"].max()
    country_counts = grouped.groupby("country")["month"].count()
    eligible = (
        grouped.groupby("country")["population"].max().sort_values(ascending=False).index.tolist()
    )
    eligible = [
        country
        for country in eligible
        if country_counts.get(country, 0) >= 12 and country_max.get(country, 0) >= 20
    ][:24]
    return grouped[grouped["country"].isin(eligible)].copy()


def load_age() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "cleaned_vaccinations_age.txt")
    cols = [
        "people_vaccinated_per_hundred",
        "people_fully_vaccinated_per_hundred",
        "people_with_booster_per_hundred",
    ]
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["date"] = pd.to_datetime(df["date"])
    return df


def parse_age_start(age_group: str) -> int:
    if "+" in age_group:
        return int(age_group.replace("+", ""))
    return int(age_group.split("-")[0])


def latest_age_breakdown(valid_countries: list[str]) -> pd.DataFrame:
    df = load_age()
    df = df[df["country"].isin(valid_countries)].copy()
    df = df.sort_values("date")
    latest = df.groupby(["country", "age_group"], as_index=False).tail(1).copy()
    latest = latest[
        (latest["people_vaccinated_per_hundred"] > 0)
        | (latest["people_fully_vaccinated_per_hundred"] > 0)
        | (latest["people_with_booster_per_hundred"] > 0)
    ]
    latest["age_start"] = latest["age_group"].map(parse_age_start)
    return latest.sort_values(["country", "age_start"])


def _append_doc_no_scroll_style(html: str, overscroll_contain: bool) -> str:
    if 'id="python-viz-no-doc-scroll"' in html:
        return html
    css = "html,body{overflow:hidden!important;margin:0;"
    if overscroll_contain:
        css += "overscroll-behavior:contain;"
    css += "}"
    inj = f'<style id="python-viz-no-doc-scroll">{css}</style>'
    if "</head>" in html:
        return html.replace("</head>", inj + "</head>", 1)
    if "<head>" in html:
        return html.replace("<head>", "<head>" + inj, 1)
    return inj + html


def _append_parent_wheel_scroll(html: str) -> str:
    """Forward wheel to parent Vue app via postMessage (Plotly/WebGL often wins document listeners)."""
    if 'id="python-viz-parent-wheel"' in html:
        return html
    inj = """<script id="python-viz-parent-wheel">
(function(){
  if (window.__pythonVizParentWheel) return;
  window.__pythonVizParentWheel = true;
  var TYPE = "python-viz-parent-wheel";
  var origin = window.location.origin || "*";
  var PLOTLY_UI = ".updatemenu,.updatemenu-container,.scrollbox,.modebar,.modebar-container,.legend,.hoverlayer,.slider-container";

  function canScrollInDirection(el, deltaY) {
    var max = el.scrollHeight - el.clientHeight;
    if (max <= 1) return false;
    if (deltaY < 0) return el.scrollTop > 0;
    if (deltaY > 0) return el.scrollTop < max - 1;
    return false;
  }

  function hasScrollableAncestor(target, deltaY) {
    var node = target;
    while (node && node !== document.body && node !== document.documentElement) {
      if (node.closest && node.closest(PLOTLY_UI)) return true;
      try {
        var style = window.getComputedStyle(node);
        var oy = style.overflowY;
        if ((oy === "auto" || oy === "scroll" || oy === "overlay") && canScrollInDirection(node, deltaY)) {
          return true;
        }
      } catch (_) {}
      node = node.parentElement || (node.parentNode && node.parentNode.host) || null;
    }
    return false;
  }

  function shouldForwardWheel(e) {
    var t = e.target;
    if (!t) return true;
    if (t.closest && t.closest(PLOTLY_UI)) return false;
    return !hasScrollableAncestor(t, e.deltaY);
  }

  window.addEventListener("wheel", function(e) {
    if (e.ctrlKey || e.metaKey) return;
    if (!window.frameElement) return;
    if (!shouldForwardWheel(e)) return;
    e.preventDefault();
    try {
      window.parent.postMessage({ type: TYPE, dy: e.deltaY }, origin);
    } catch (_) {}
  }, { capture: true, passive: false });
})();
</script>"""
    if "<head>" in html:
        return html.replace("<head>", "<head>" + inj, 1)
    if "</head>" in html:
        return html.replace("</head>", inj + "</head>", 1)
    return inj + html


def write_figure(
    fig,
    filename: str,
    height: int = 560,
    *,
    margin: dict | None = None,
    overscroll_contain: bool = False,
) -> None:
    m = dict(l=56, r=32, t=64, b=56)
    if margin:
        m.update(margin)
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#fffaf2",
        plot_bgcolor="#fffaf2",
        font=dict(family="Segoe UI, Microsoft YaHei, sans-serif", color="#1f2a1f"),
        margin=m,
        height=height,
    )
    out_path = OUTPUT_DIR / filename
    fig.write_html(
        out_path,
        include_plotlyjs=True,
        full_html=True,
        config={
            "responsive": True,
            "displaylogo": False,
            # Avoid Plotly capturing wheel for zoom/pan while we forward scroll to the parent page.
            "scrollZoom": False,
        },
    )
    html = out_path.read_text(encoding="utf-8")
    html = _append_doc_no_scroll_style(html, overscroll_contain)
    html = _append_parent_wheel_scroll(html)
    out_path.write_text(html, encoding="utf-8")

    if (ROOT / "dist").is_dir():
        dist_viz = ROOT / "dist" / "mortality-vaccination"
        dist_viz.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out_path, dist_viz / filename)
