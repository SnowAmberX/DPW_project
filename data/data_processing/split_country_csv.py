from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_FILE = ROOT_DIR / "data" / "processed_data" / "cleaned_panel_country_day.csv"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "country_data"


def sanitize_filename(name: str) -> str:
    # Keep filenames portable across macOS/Windows/Linux.
    sanitized = re.sub(r"[\\/:*?\"<>|]", "_", str(name).strip())
    sanitized = re.sub(r"\s+", " ", sanitized).strip(" .")
    return sanitized or "Unknown"


def split_country_csv(
    input_file: Path,
    output_dir: Path,
    country_col: str = "country",
    code_col: str = "code",
) -> tuple[int, int]:
    df = pd.read_csv(input_file)

    required_cols = {country_col, code_col}
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    output_dir.mkdir(parents=True, exist_ok=True)

    file_count = 0
    row_count = 0
    used_names: dict[str, int] = {}

    for country, group in df.groupby(country_col, sort=True):
        if pd.isna(country):
            continue

        country_name = str(country)
        base_name = sanitize_filename(country_name)

        # Handle sanitized-name collisions deterministically.
        if base_name not in used_names:
            used_names[base_name] = 0
            final_name = base_name
        else:
            used_names[base_name] += 1
            code_value = str(group[code_col].iloc[0]) if not group.empty else "UNK"
            final_name = f"{base_name}_{sanitize_filename(code_value)}_{used_names[base_name]}"

        out_file = output_dir / f"{final_name}.csv"
        group.sort_values("date").to_csv(out_file, index=False)

        file_count += 1
        row_count += len(group)

    return file_count, row_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split panel data into one CSV file per country.")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_FILE,
        help=f"Path to source CSV (default: {DEFAULT_INPUT_FILE})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for country CSV files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument("--country-col", default="country", help="Country column name")
    parser.add_argument("--code-col", default="code", help="Country code column name")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    file_count, row_count = split_country_csv(
        input_file=args.input,
        output_dir=args.output_dir,
        country_col=args.country_col,
        code_col=args.code_col,
    )
    print(f"Done. Generated {file_count} country CSV files in: {args.output_dir}")
    print(f"Total rows written: {row_count}")


if __name__ == "__main__":
    main()