from __future__ import annotations

from curve_fit import build as build_curve_fit
from group_matrix import build as build_group_matrix
from quarter_summary import build as build_quarter_summary
from rollout_paths import build as build_rollout_paths


def main() -> None:
    build_rollout_paths()
    build_group_matrix()
    build_quarter_summary()
    build_curve_fit()


if __name__ == "__main__":
    main()
