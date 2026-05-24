"""Generate static Plotly HTML and CSV assets for the cases-vaccination page."""

from __future__ import annotations

from pathlib import Path
import runpy


def main() -> None:
    script = Path(__file__).with_name("cases_vaccination_analysis.py")
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
