"""
Fill isolated runs of zeros in vaccination / case / death columns (2022–2023 only),
plus pre-2024 trailing-zero repair for chart stability.

cleaned_compact.txt
  • new_cases, new_deaths (+ smoothed): zero runs between two positive neighbors get
    the flat average (prev + next) / 2 when min(prev,next) >= RATIO * max(prev,next).
  • people_vaccinated, total_vaccinations (cumulative): same detection, but gaps are
    filled with linear interpolation from prev to next when next >= prev (skipped if
    next < prev).
  • Before 2024-01-01: if a day is still zero after the above, and the last non-zero
    before it is clearly above the previous calendar month's series mean, impute:
    – flow/smoothed columns → that previous month's mean;
    – cumulative vaccination columns → forward-fill the last non-zero (plateau).

cleaned_vaccinations_age.txt (optional, --age-file)
  • people_vaccinated_per_hundred, people_fully_vaccinated_per_hundred,
    people_with_booster_per_hundred: linear interpolation between neighbors when
    next >= prev; otherwise skipped.

Usage (from repo root):
  python scripts/fill_compact_zeros_between_large.py
  python scripts/fill_compact_zeros_between_large.py --dry-run
  python scripts/fill_compact_zeros_between_large.py --no-age-file
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

# Neighbors must be within the same order of magnitude (tune if needed).
MIN_NEIGHBOR_RATIO = 0.05  # min(prev, next) >= 0.05 * max(prev, next)

DATE_START = pd.Timestamp("2022-01-01")
DATE_END = pd.Timestamp("2023-12-31")
# Trailing-zero repair: all dates strictly before this (entire pre-2024 history).
PRE_2024_CUTOFF = pd.Timestamp("2024-01-01")
# Last non-zero before a zero must be at least this fraction of the imputed baseline.
TRAIL_LAST_GE_PREV_MONTH_MEAN = 0.85

FLAT_COLUMNS = (
    "new_cases",
    "new_deaths",
    "new_cases_smoothed",
    "new_deaths_smoothed",
)

# Cumulative stock counts: interpolate linearly across zero gaps (no flat average).
LINEAR_STOCK_COLUMNS = ("people_vaccinated", "total_vaccinations")

AGE_FILE = "cleaned_vaccinations_age.txt"
AGE_COLUMNS = (
    "people_vaccinated_per_hundred",
    "people_fully_vaccinated_per_hundred",
    "people_with_booster_per_hundred",
)


def _find_project_root() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in [here.parent, *here.parents]:
        if (candidate / "data").is_dir() and (candidate / "src").is_dir():
            return candidate
    raise RuntimeError("Could not find project root (data/ + src/).")


def _is_effective_zero(x: float) -> bool:
    return not np.isfinite(x) or abs(float(x)) < 1e-12


def fill_column(
    values: np.ndarray,
    in_range: np.ndarray,
    *,
    linear: bool,
) -> tuple[np.ndarray, int]:
    """Return (new_values, n_cells_filled)."""
    out = values.astype(float, copy=True)
    n = len(out)
    filled = 0
    i = 0
    while i < n:
        if not in_range[i] or not _is_effective_zero(out[i]):
            i += 1
            continue
        start = i
        while i < n and in_range[i] and _is_effective_zero(out[i]):
            i += 1
        end = i - 1

        j = start - 1
        while j >= 0 and _is_effective_zero(out[j]):
            j -= 1
        if j < 0:
            continue
        prev_v = float(out[j])
        if prev_v <= 0:
            continue

        k = end + 1
        while k < n and _is_effective_zero(out[k]):
            k += 1
        if k >= n:
            continue
        next_v = float(out[k])
        if next_v <= 0:
            continue

        lo, hi = min(prev_v, next_v), max(prev_v, next_v)
        if lo < MIN_NEIGHBOR_RATIO * hi:
            continue

        if linear:
            if next_v < prev_v:
                continue
            span = float(k - j)
            if span <= 1.0:
                continue
            for t in range(start, end + 1):
                alpha = (float(t) - float(j)) / span
                out[t] = prev_v + alpha * (next_v - prev_v)
                filled += 1
        else:
            fill_val = (prev_v + next_v) / 2.0
            for t in range(start, end + 1):
                out[t] = fill_val
                filled += 1

    return out, filled


def _fill_pre2024_trailing_after_large(
    arr: np.ndarray,
    dates: pd.DatetimeIndex,
    *,
    is_stock: bool,
) -> tuple[np.ndarray, int]:
    """Pre-2024 zeros after a high stretch vs prior-month mean (see module docstring)."""
    out = arr.astype(float, copy=True)
    n = len(out)
    if n == 0:
        return out, 0
    filled = 0
    ym = dates.to_period("M")
    means = pd.Series(arr, index=ym).groupby(level=0).mean()

    # One walk-back per calendar month in this country (not per day).
    baseline_for_month: dict[pd.Period, float] = {}
    for mrow in pd.Series(ym, copy=False).unique():
        pm = mrow - 1
        val: float | None = None
        for _ in range(800):
            if pm in means.index:
                v = float(means.loc[pm])
                if np.isfinite(v) and v > 0:
                    val = v
                    break
            pm -= 1
        baseline_for_month[mrow] = val if val is not None else float("nan")

    row_baseline = np.array([baseline_for_month[m] for m in ym], dtype=float)

    for pos in range(n):
        if dates[pos] >= PRE_2024_CUTOFF:
            continue
        if not _is_effective_zero(out[pos]):
            continue

        pm_mean = float(row_baseline[pos])
        if not np.isfinite(pm_mean) or pm_mean <= 0:
            continue

        j = pos - 1
        while j >= 0 and _is_effective_zero(out[j]):
            j -= 1
        if j < 0:
            continue
        lv = float(out[j])
        if lv < TRAIL_LAST_GE_PREV_MONTH_MEAN * pm_mean:
            continue

        if is_stock:
            out[pos] = lv
        else:
            out[pos] = pm_mean
        filled += 1

    return out, filled


def apply_pre2024_trailing_to_compact(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    all_cols = list(FLAT_COLUMNS) + list(LINEAR_STOCK_COLUMNS)
    counts: dict[str, int] = {c: 0 for c in all_cols}
    stock_set = frozenset(LINEAR_STOCK_COLUMNS)

    for col in all_cols:
        is_stock = col in stock_set
        for _, sub in df.groupby("country", sort=False):
            order = sub["date"].to_numpy().argsort(kind="mergesort")
            idx = sub.index.to_numpy()[order]
            arr = sub[col].to_numpy(dtype=float, copy=False)[order]
            dates = pd.DatetimeIndex(sub["date"].to_numpy()[order])
            new_arr, n = _fill_pre2024_trailing_after_large(arr, dates, is_stock=is_stock)
            if n:
                df.loc[idx, col] = new_arr
                counts[col] += n

    return df, counts


def process_compact(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    all_cols = list(FLAT_COLUMNS) + list(LINEAR_STOCK_COLUMNS)
    counts: dict[str, int] = {c: 0 for c in all_cols}

    for _, sub in df.groupby("country", sort=False):
        order = sub["date"].to_numpy().argsort(kind="mergesort")
        idx = sub.index.to_numpy()[order]
        dates = pd.DatetimeIndex(sub["date"].to_numpy()[order]).to_numpy()
        d0 = np.datetime64(DATE_START.to_datetime64(), "D")
        d1 = np.datetime64(DATE_END.to_datetime64(), "D")
        in_range = (dates >= d0) & (dates <= d1)

        for col in FLAT_COLUMNS:
            arr = sub[col].to_numpy(dtype=float, copy=False)[order]
            new_arr, n = fill_column(arr, in_range, linear=False)
            if n:
                df.loc[idx, col] = new_arr
                counts[col] += n

        for col in LINEAR_STOCK_COLUMNS:
            arr = sub[col].to_numpy(dtype=float, copy=False)[order]
            new_arr, n = fill_column(arr, in_range, linear=True)
            if n:
                df.loc[idx, col] = new_arr
                counts[col] += n

    return df, counts


def process_age_vaccinations(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    counts: dict[str, int] = {c: 0 for c in AGE_COLUMNS}

    gcols = ["country", "age_group"]
    for _, sub in df.groupby(gcols, sort=False):
        order = sub["date"].to_numpy().argsort(kind="mergesort")
        idx = sub.index.to_numpy()[order]
        dates = pd.DatetimeIndex(sub["date"].to_numpy()[order]).to_numpy()
        d0 = np.datetime64(DATE_START.to_datetime64(), "D")
        d1 = np.datetime64(DATE_END.to_datetime64(), "D")
        in_range = (dates >= d0) & (dates <= d1)

        for col in AGE_COLUMNS:
            arr = sub[col].to_numpy(dtype=float, copy=False)[order]
            new_arr, n = fill_column(arr, in_range, linear=True)
            if n:
                df.loc[idx, col] = new_arr
                counts[col] += n

    return df, counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill zero gaps in cleaned_compact (2022–2023).")
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Input CSV (default: <root>/data/cleaned_compact.txt)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV (default: overwrite input)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute changes but do not write files.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="When overwriting input, skip copying to .bak (not recommended).",
    )
    parser.add_argument(
        "--no-age-file",
        action="store_true",
        help="Skip data/cleaned_vaccinations_age.txt.",
    )
    args = parser.parse_args()

    root = _find_project_root()
    in_path = args.input or (root / "data" / "cleaned_compact.txt")
    out_path = args.output or in_path

    if not in_path.is_file():
        raise SystemExit(f"Input not found: {in_path}")

    print(f"Reading {in_path} ...")
    df = pd.read_csv(in_path)
    for col in list(FLAT_COLUMNS) + list(LINEAR_STOCK_COLUMNS):
        if col not in df.columns:
            raise SystemExit(f"Missing column {col!r} in CSV.")

    df2, counts = process_compact(df)
    total = sum(counts.values())
    print("[compact] Sandwich (2022-23) cells filled by column:", counts)
    print("[compact] Sandwich total:", total)

    df2, trail = apply_pre2024_trailing_to_compact(df2)
    print("[compact] Pre-2024 trailing cells filled by column:", trail)
    print("[compact] Pre-2024 trailing total:", sum(trail.values()))

    age_path = root / "data" / AGE_FILE
    age_counts: dict[str, int] = {}
    age_df2: pd.DataFrame | None = None
    if not args.no_age_file:
        if not age_path.is_file():
            print(f"Warning: age file not found, skip: {age_path}")
        else:
            print(f"Reading {age_path} ...")
            age_df = pd.read_csv(age_path)
            for col in AGE_COLUMNS:
                if col not in age_df.columns:
                    raise SystemExit(f"Missing column {col!r} in age CSV.")
            age_df2, age_counts = process_age_vaccinations(age_df)
            print("[age] Cells filled by column:", age_counts)
            print("[age] Total numeric cells filled:", sum(age_counts.values()))

    if args.dry_run:
        print("Dry run: no files written.")
        return

    if out_path.resolve() == in_path.resolve() and not args.no_backup:
        bak = in_path.with_suffix(in_path.suffix + ".bak")
        print(f"Backup (compact) -> {bak}")
        shutil.copy2(in_path, bak)

    print(f"Writing {out_path} ...")
    df2.to_csv(out_path, index=False)

    if age_df2 is not None and not args.no_age_file:
        if not args.no_backup:
            age_bak = age_path.with_suffix(age_path.suffix + ".bak")
            print(f"Backup (age) -> {age_bak}")
            shutil.copy2(age_path, age_bak)
        print(f"Writing {age_path} ...")
        age_df2.to_csv(age_path, index=False)

    print("Done.")


if __name__ == "__main__":
    main()
