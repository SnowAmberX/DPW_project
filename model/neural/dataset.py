import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset


STATIC_FEATURE_COLUMNS = [
    "population",
    "population_density",
    "median_age",
    "gdp_per_capita",
    "hospital_beds_per_thousand",
]


@dataclass
class DatasetArtifacts:
    countries: List[str]
    country_to_idx: Dict[str, int]
    code_to_name: Dict[str, str]
    name_to_code: Dict[str, str]
    static_features: torch.Tensor
    adjacency: torch.Tensor
    edge_index: torch.Tensor
    edge_weight: torch.Tensor


def _safe_standardize(arr: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = arr.mean(axis=0)
    std = arr.std(axis=0)
    std = np.where(std < 1e-8, 1.0, std)
    z = (arr - mean) / std
    return z, mean, std


def _normalize_by_median(values: np.ndarray, floor: float = 1e-6) -> np.ndarray:
    values = np.clip(values.astype(np.float64), a_min=floor, a_max=None)
    median = np.median(values)
    median = max(float(median), floor)
    return values / median


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    a = min(1.0, max(0.0, a))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def _load_country_latlng(meta_path: Path) -> Dict[str, Tuple[float, float]]:
    raw = json.loads(meta_path.read_text(encoding="utf-8"))
    latlng: Dict[str, Tuple[float, float]] = {}
    for item in raw:
        code = item.get("cca3")
        coords = item.get("latlng")
        if (
            isinstance(code, str)
            and isinstance(coords, list)
            and len(coords) == 2
            and all(isinstance(v, (int, float)) for v in coords)
        ):
            latlng[code] = (float(coords[0]), float(coords[1]))
    return latlng


def _build_gravity_adjacency(
    countries: List[str],
    population: Dict[str, float],
    gdp_per_capita: Dict[str, float],
    latlng: Dict[str, Tuple[float, float]],
    tau_km: float = 3000.0,
    top_k: int = 8,
    self_loop: float = 2.0,
) -> np.ndarray:
    """Build gravity-based adjacency with per-node top-k pruning."""
    n = len(countries)
    if n == 0:
        return np.zeros((0, 0), dtype=np.float32)

    pop = np.array([population.get(c, 1.0) for c in countries], dtype=np.float64)
    gdp = np.array([gdp_per_capita.get(c, 1.0) for c in countries], dtype=np.float64)
    pop_norm = _normalize_by_median(pop, floor=1e-6)
    gdp_norm = _normalize_by_median(gdp, floor=1e-6)

    tau = max(float(tau_km), 1.0)
    raw = np.zeros((n, n), dtype=np.float64)

    for i, ci in enumerate(countries):
        lat_i, lon_i = latlng[ci]
        for j, cj in enumerate(countries):
            if i == j:
                continue
            lat_j, lon_j = latlng[cj]
            distance = _haversine_km(lat_i, lon_i, lat_j, lon_j)
            w_ij = (
                (pop_norm[i] * pop_norm[j]) ** 0.5
                * (gdp_norm[i] * gdp_norm[j]) ** 0.3
                * math.exp(-distance / tau)
            )
            raw[i, j] = w_ij

    # Per-node top-k pruning (directed before symmetrisation).
    k = max(0, min(int(top_k), n - 1))
    pruned = np.zeros_like(raw)
    if k > 0:
        for i in range(n):
            row = raw[i].copy()
            row[i] = 0.0
            if k < n - 1:
                idx = np.argpartition(row, -k)[-k:]
            else:
                idx = np.arange(n)
                idx = idx[idx != i]
            idx = idx[row[idx] > 0.0]
            pruned[i, idx] = row[idx]

    w = 0.5 * (pruned + pruned.T)
    np.fill_diagonal(w, float(self_loop))

    deg = w.sum(axis=1)
    deg[deg <= 1e-12] = 1.0
    d_inv_sqrt = 1.0 / np.sqrt(deg)
    w_norm = w * d_inv_sqrt[:, None] * d_inv_sqrt[None, :]
    return w_norm.astype(np.float32)


def _adjacency_to_edge_index_weight(
    adj: np.ndarray,
) -> Tuple[torch.Tensor, torch.Tensor]:
    src, dst = np.nonzero(adj)
    edge_index = np.vstack([src, dst])
    edge_weight = adj[src, dst]
    return (
        torch.tensor(edge_index, dtype=torch.long),
        torch.tensor(edge_weight, dtype=torch.float32),
    )


class COVIDSpatioTemporalDataset(Dataset):
    """Spatio-temporal dataset with direct log-level forecasting target."""

    def __init__(
        self,
        data_csv_path: Path,
        countries_meta_path: Path,
        seq_len: int = 21,
        horizon: int = 60,
        distance_threshold_km: float = 10000.0,
        kernel_scale_km: float = 3000.0,
        density_exponent: float = 0.5,
        graph_top_k: int = 8,
        outbreak_aug_prob: float = 0.3,
        outbreak_baseline_max: float = 5.0,
        use_seed_indicator: bool = True,
        seed_curve_amplify_min: float = 1.0,
        seed_curve_amplify_max: float = 1.15,
        random_seed: int = 42,
    ) -> None:
        self.seq_len = seq_len
        self.horizon = horizon
        self.outbreak_aug_prob = float(np.clip(outbreak_aug_prob, 0.0, 1.0))
        self.outbreak_baseline_max = max(0.0, float(outbreak_baseline_max))
        self.use_seed_indicator = bool(use_seed_indicator)
        self.seed_curve_amplify_min = max(0.0, float(seed_curve_amplify_min))
        self.seed_curve_amplify_max = max(
            self.seed_curve_amplify_min, float(seed_curve_amplify_max)
        )
        self.rng = np.random.default_rng(seed=random_seed)
        self.train_cutoff: int | None = None

        usecols = [
            "date",
            "country",
            "code",
            "new_cases_smoothed",
            *STATIC_FEATURE_COLUMNS,
        ]
        df = pd.read_csv(data_csv_path, usecols=usecols)

        df = df[df["code"].astype(str).str.fullmatch(r"[A-Z]{3}", na=False)].copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date", "code"])

        for col in ["new_cases_smoothed", *STATIC_FEATURE_COLUMNS]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        latlng = _load_country_latlng(countries_meta_path)
        valid_codes = sorted(set(df["code"].tolist()))
        valid_codes = [c for c in valid_codes if c in latlng]
        df = df[df["code"].isin(valid_codes)].copy()

        # --- Static features ---
        static_df = (
            df.groupby("code", as_index=False)[STATIC_FEATURE_COLUMNS]
            .median(numeric_only=True)
            .sort_values("code")
        )
        for col in STATIC_FEATURE_COLUMNS:
            col_med = static_df[col].median(skipna=True)
            static_df[col] = static_df[col].fillna(
                col_med if pd.notna(col_med) else 0.0
            )

        self.countries = static_df["code"].tolist()
        self.country_to_idx = {c: i for i, c in enumerate(self.countries)}

        code_name_df = df[["code", "country"]].dropna().drop_duplicates(subset=["code"])
        code_to_name_raw = {
            row["code"]: str(row["country"]) for _, row in code_name_df.iterrows()
        }
        self.code_to_name = {c: str(code_to_name_raw.get(c, c)) for c in self.countries}
        self.name_to_code = {
            str(name).lower(): code for code, name in self.code_to_name.items()
        }

        population_dict = {
            row["code"]: float(max(row["population"], 1.0))
            for _, row in static_df[["code", "population"]].iterrows()
        }
        gdp_dict = {
            row["code"]: float(max(row["gdp_per_capita"], 1e-3))
            for _, row in static_df[["code", "gdp_per_capita"]].iterrows()
        }
        latlng = {c: latlng[c] for c in self.countries}

        static_matrix = static_df[STATIC_FEATURE_COLUMNS].to_numpy(dtype=np.float32)
        static_matrix, _, _ = _safe_standardize(static_matrix)
        self.static_features_np = static_matrix.astype(np.float32)

        # --- Time-series: log level ---
        ts = df.pivot_table(
            index="date",
            columns="code",
            values="new_cases_smoothed",
            aggfunc="mean",
        ).sort_index()
        ts = ts.reindex(columns=self.countries)
        ts = ts.fillna(0.0)
        ts_values = ts.to_numpy(dtype=np.float32)
        ts_values = np.clip(ts_values, a_min=0.0, a_max=None)

        # Direct modeling target: log(new_cases).
        self.cases = np.log1p(ts_values).astype(np.float32)  # (T, N)

        # Kept for backward compatibility with previous function signatures.
        _ = distance_threshold_km
        _ = density_exponent

        adjacency = _build_gravity_adjacency(
            countries=self.countries,
            population=population_dict,
            gdp_per_capita=gdp_dict,
            latlng=latlng,
            tau_km=kernel_scale_km,
            top_k=graph_top_k,
            self_loop=2.0,
        )

        edge_index, edge_weight = _adjacency_to_edge_index_weight(adjacency)

        # Report connectivity stats
        n_countries = len(self.countries)
        n_edges = edge_index.shape[1] - n_countries  # exclude self-loops
        avg_degree = n_edges / max(n_countries, 1)
        print(
            f"[dataset] {n_countries} countries | {n_edges} directed edges "
            f"(avg degree {avg_degree:.1f}) | gravity_tau {kernel_scale_km:.0f} km "
            f"| top_k {graph_top_k}"
        )

        self.artifacts = DatasetArtifacts(
            countries=self.countries,
            country_to_idx=self.country_to_idx,
            code_to_name=self.code_to_name,
            name_to_code=self.name_to_code,
            static_features=torch.tensor(self.static_features_np, dtype=torch.float32),
            adjacency=torch.tensor(adjacency, dtype=torch.float32),
            edge_index=edge_index,
            edge_weight=edge_weight,
        )

        self.total_time = self.cases.shape[0]
        self.num_nodes = self.cases.shape[1]
        self.static_dim = self.static_features_np.shape[1]
        self.input_dim = 1 + self.static_dim + int(self.use_seed_indicator)

        print(
            "[dataset] outbreak augmentation "
            f"p={self.outbreak_aug_prob:.2f} | "
            f"baseline<= {self.outbreak_baseline_max:.1f} | "
            f"seed_indicator={self.use_seed_indicator}"
        )

    def set_train_cutoff(self, cutoff: int | None) -> None:
        self.train_cutoff = None if cutoff is None else max(0, int(cutoff))

    def _is_train_index(self, idx: int) -> bool:
        if self.train_cutoff is None:
            return True
        return idx < self.train_cutoff

    def _build_smooth_low_baseline(self, num_nodes: int) -> np.ndarray:
        if self.outbreak_baseline_max <= 0.0:
            return np.zeros((num_nodes, self.seq_len), dtype=np.float32)

        starts = self.rng.uniform(
            0.0, self.outbreak_baseline_max, size=(num_nodes, 1)
        ).astype(np.float32)
        ends = self.rng.uniform(
            0.0, self.outbreak_baseline_max, size=(num_nodes, 1)
        ).astype(np.float32)
        alpha = np.linspace(0.0, 1.0, self.seq_len, dtype=np.float32)[None, :]
        baseline_cases = starts * (1.0 - alpha) + ends * alpha
        return np.log1p(baseline_cases).astype(np.float32)

    def _apply_outbreak_augmentation(
        self, idx: int, hist: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        seed_flag = np.zeros((self.num_nodes,), dtype=np.float32)
        if not self._is_train_index(idx):
            return hist, seed_flag
        if self.outbreak_aug_prob <= 0.0 or self.rng.random() >= self.outbreak_aug_prob:
            return hist, seed_flag

        seed_idx = int(self.rng.integers(0, self.num_nodes))
        seed_flag[seed_idx] = 1.0

        # Build smooth, low non-zero baseline to avoid distribution spikes.
        aug_hist = self._build_smooth_low_baseline(self.num_nodes)

        # Keep seed history realistic by preserving/softly amplifying original trajectory.
        amp = float(
            self.rng.uniform(self.seed_curve_amplify_min, self.seed_curve_amplify_max)
        )
        seed_cases = np.expm1(hist[seed_idx].astype(np.float64)) * amp
        seed_cases = np.clip(seed_cases, a_min=0.0, a_max=1e9)
        aug_hist[seed_idx] = np.log1p(seed_cases).astype(np.float32)

        return aug_hist, seed_flag

    def __len__(self) -> int:
        return max(0, self.total_time - self.seq_len - self.horizon + 1)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        # x shape: (num_nodes, seq_len, 1 + static_dim [+ seed_indicator])
        hist = self.cases[idx : idx + self.seq_len, :].T  # (N, seq_len)
        target = self.cases[
            idx + self.seq_len : idx + self.seq_len + self.horizon, :
        ].T  # (N, horizon)

        hist, seed_flag = self._apply_outbreak_augmentation(idx=idx, hist=hist)

        num_nodes = self.num_nodes
        static_dim = self.static_dim
        x = np.zeros((num_nodes, self.seq_len, self.input_dim), dtype=np.float32)
        x[:, :, 0] = hist
        x[:, :, 1 : 1 + static_dim] = self.static_features_np[:, None, :]
        if self.use_seed_indicator:
            x[:, :, -1] = seed_flag[:, None]

        return (
            torch.tensor(x, dtype=torch.float32),
            torch.tensor(target, dtype=torch.float32),
        )


def split_train_val(
    dataset: COVIDSpatioTemporalDataset, val_ratio: float = 0.15
) -> Tuple[torch.utils.data.Subset, torch.utils.data.Subset]:
    n = len(dataset)
    if n == 0:
        raise ValueError(
            "No usable samples were generated. Adjust seq_len/horizon or data filters."
        )
    if n <= 1:
        return torch.utils.data.Subset(dataset, [0]), torch.utils.data.Subset(
            dataset, [0]
        )

    split = int(n * (1.0 - val_ratio))
    split = min(max(split, 1), n - 1)
    train_idx = list(range(0, split))
    val_idx = list(range(split, n))
    return torch.utils.data.Subset(dataset, train_idx), torch.utils.data.Subset(
        dataset, val_idx
    )


def create_dataloaders(
    data_csv_path: Path,
    countries_meta_path: Path,
    seq_len: int,
    horizon: int,
    batch_size: int,
    val_ratio: float = 0.15,
    distance_threshold_km: float = 10000.0,
    kernel_scale_km: float = 3000.0,
    density_exponent: float = 0.5,
    graph_top_k: int = 8,
    outbreak_aug_prob: float = 0.3,
    outbreak_baseline_max: float = 5.0,
    use_seed_indicator: bool = True,
    seed_curve_amplify_min: float = 1.0,
    seed_curve_amplify_max: float = 1.15,
    random_seed: int = 42,
) -> Tuple[DataLoader, DataLoader, DatasetArtifacts, COVIDSpatioTemporalDataset]:
    dataset = COVIDSpatioTemporalDataset(
        data_csv_path=data_csv_path,
        countries_meta_path=countries_meta_path,
        seq_len=seq_len,
        horizon=horizon,
        distance_threshold_km=distance_threshold_km,
        kernel_scale_km=kernel_scale_km,
        density_exponent=density_exponent,
        graph_top_k=graph_top_k,
        outbreak_aug_prob=outbreak_aug_prob,
        outbreak_baseline_max=outbreak_baseline_max,
        use_seed_indicator=use_seed_indicator,
        seed_curve_amplify_min=seed_curve_amplify_min,
        seed_curve_amplify_max=seed_curve_amplify_max,
        random_seed=random_seed,
    )
    train_ds, val_ds = split_train_val(dataset, val_ratio=val_ratio)
    if hasattr(train_ds, "indices") and len(train_ds.indices) > 0:
        dataset.set_train_cutoff(int(max(train_ds.indices)) + 1)
    else:
        dataset.set_train_cutoff(None)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)
    return train_loader, val_loader, dataset.artifacts, dataset
