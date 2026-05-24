from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd


MAX_QUARTER = "2023Q4"


def _find_frontend_root() -> Path:
    current = Path(__file__).resolve().parent
    for candidate in [current, *current.parents]:
        if (candidate / "public").exists() and (candidate / "src").exists():
            return candidate
    raise RuntimeError("Unable to locate frontend root containing public/ and src/")


ROOT = _find_frontend_root()
DATA_DIR = ROOT / "public" / "overview"
OUTPUT_DIR = ROOT / "public" / "overview"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def quarter_ordinal(quarter: str) -> int | None:
    text = str(quarter or "")
    if len(text) != 6 or text[4] != "Q":
        return None
    try:
        return int(text[:4]) * 4 + int(text[5]) - 1
    except ValueError:
        return None


def is_quarter_on_or_before(quarter: str, max_quarter: str = MAX_QUARTER) -> bool:
    value = quarter_ordinal(quarter)
    max_value = quarter_ordinal(max_quarter)
    return value is not None and max_value is not None and value <= max_value


def sort_quarters(values: list[str]) -> list[str]:
    return sorted(
        [q for q in values if is_quarter_on_or_before(q)],
        key=lambda q: quarter_ordinal(q) or 0,
    )


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name)


def read_group_long() -> pd.DataFrame:
    long_path = DATA_DIR / "group_quarterly_long.csv"
    if long_path.exists():
        df = pd.read_csv(long_path)
        df = df.rename(columns={"country": "group"})
        return df[["group", "quarter", "metric", "value"]].copy()

    wide = pd.read_csv(DATA_DIR / "group_quarterly_rollout_enriched.csv")
    wide = wide.rename(columns={"country": "group"})
    metrics = ["rollout_speed", "first_dose_progress", "full_vaccination_progress"]
    return wide.melt(id_vars=["group", "quarter"], value_vars=metrics, var_name="metric", value_name="value")


def group_order() -> dict[str, int]:
    path = DATA_DIR / "group_meta.csv"
    if not path.exists():
        return {}
    meta = pd.read_csv(path).rename(columns={"country": "group", "name": "group"})
    if "display_order" not in meta.columns:
        return {}
    return {
        str(row["group"]): int(row["display_order"])
        for _, row in meta.dropna(subset=["group", "display_order"]).iterrows()
    }


def add_embed_helpers(html: str) -> str:
    if 'id="overview-python-embed-style"' not in html:
        css = (
            '<style id="overview-python-embed-style">'
            "html,body{overflow:hidden!important;margin:0;overscroll-behavior:contain;}"
            "</style>"
        )
        html = html.replace("</head>", css + "</head>", 1) if "</head>" in html else css + html

    if 'id="overview-python-parent-wheel"' not in html:
        script = """<script id="overview-python-parent-wheel">
(function(){
  if (window.__overviewPythonParentWheel) return;
  window.__overviewPythonParentWheel = true;
  var TYPE = "python-viz-parent-wheel";
  var origin = window.location.origin || "*";
  window.addEventListener("wheel", function(e) {
    if (e.ctrlKey || e.metaKey || !window.frameElement) return;
    e.preventDefault();
    try { window.parent.postMessage({ type: TYPE, dy: e.deltaY }, origin); } catch (_) {}
  }, { capture: true, passive: false });
})();
</script>"""
        html = html.replace("<head>", "<head>" + script, 1) if "<head>" in html else script + html
    return html


def write_figure(fig, filename: str, height: int, margin: dict | None = None) -> None:
    m = dict(l=58, r=34, t=66, b=54)
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
        config={"responsive": True, "displaylogo": False, "displayModeBar": False, "scrollZoom": False},
    )
    out_path.write_text(add_embed_helpers(out_path.read_text(encoding="utf-8")), encoding="utf-8")

    dist_viz = ROOT / "dist" / "overview"
    if dist_viz.is_dir():
        shutil.copy2(out_path, dist_viz / filename)
