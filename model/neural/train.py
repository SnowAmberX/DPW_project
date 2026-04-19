import argparse
import json
from pathlib import Path
from typing import Dict

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from dataset import create_dataloaders
from gnn_lstm import GNNRNNForecastModel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train GNN + LSTM/GRU COVID forecasting model."
    )
    parser.add_argument("--data", type=str, default="../../data/raw_data/compact.csv")
    parser.add_argument(
        "--countries-meta", type=str, default="./artifacts/countries_meta.json"
    )
    parser.add_argument("--seq-len", type=int, default=21)
    parser.add_argument("--horizon", type=int, default=60)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--rnn-type", type=str, choices=["lstm", "gru"], default="gru")
    parser.add_argument("--rnn-layers", type=int, default=1)
    parser.add_argument("--gat-heads", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--weight-decay", type=float, default=1e-5)
    parser.add_argument(
        "--early-stopping-patience",
        type=int,
        default=10,
        help="Stop training if validation MSE does not improve for this many epochs.",
    )
    parser.add_argument(
        "--early-stopping-min-delta",
        type=float,
        default=0.0,
        help="Minimum validation MSE decrease to qualify as an improvement.",
    )
    parser.add_argument(
        "--distance-threshold",
        type=float,
        default=10000.0,
        help="Max distance (km) for adjacency edges. Default 10000 (long-range).",
    )
    parser.add_argument(
        "--kernel-scale",
        type=float,
        default=3000.0,
        help="Gaussian kernel scale tau (km). Smaller = more localised. Default 3000.",
    )
    parser.add_argument(
        "--density-exponent",
        type=float,
        default=0.5,
        help="Exponent on population-density factor in edge weights. 0 disables. Default 0.5.",
    )
    parser.add_argument(
        "--graph-top-k",
        type=int,
        default=8,
        help="Per-node top-k neighbours kept in gravity graph.",
    )
    parser.add_argument(
        "--outbreak-aug-prob",
        type=float,
        default=0.3,
        help="Probability of single-seed outbreak augmentation per training sample.",
    )
    parser.add_argument(
        "--outbreak-baseline-max",
        type=float,
        default=5.0,
        help="Upper bound for low baseline cases (before log1p) in augmentation.",
    )
    parser.add_argument(
        "--disable-seed-indicator",
        action="store_true",
        help="Disable seed indicator feature channel.",
    )
    parser.add_argument(
        "--seed-curve-amplify-min",
        type=float,
        default=1.0,
        help="Minimum multiplicative factor for seed country history in augmentation.",
    )
    parser.add_argument(
        "--seed-curve-amplify-max",
        type=float,
        default=1.15,
        help="Maximum multiplicative factor for seed country history in augmentation.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Random seed for dataset augmentation sampling.",
    )
    parser.add_argument(
        "--checkpoint", type=str, default="./artifacts/checkpoint_gnn_rnn.pt"
    )
    return parser.parse_args()


def _evaluate(
    model: nn.Module,
    dataloader: torch.utils.data.DataLoader,
    edge_index: torch.Tensor,
    edge_weight: torch.Tensor,
    criterion: nn.Module,
    device: torch.device,
) -> float:
    model.eval()
    losses = []
    with torch.no_grad():
        for x, y in dataloader:
            x = x.to(device)
            y = y.to(device)
            pred = model(x, edge_index, edge_weight)
            loss = criterion(pred, y)
            losses.append(loss.item())
    return float(np.mean(losses)) if losses else float("nan")


def train() -> None:
    args = parse_args()

    data_path = Path(args.data).resolve()
    meta_path = Path(args.countries_meta).resolve()
    ckpt_path = Path(args.checkpoint).resolve()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    train_loader, val_loader, artifacts, dataset = create_dataloaders(
        data_csv_path=data_path,
        countries_meta_path=meta_path,
        seq_len=args.seq_len,
        horizon=args.horizon,
        batch_size=args.batch_size,
        val_ratio=args.val_ratio,
        distance_threshold_km=args.distance_threshold,
        kernel_scale_km=args.kernel_scale,
        density_exponent=args.density_exponent,
        graph_top_k=args.graph_top_k,
        outbreak_aug_prob=args.outbreak_aug_prob,
        outbreak_baseline_max=args.outbreak_baseline_max,
        use_seed_indicator=not args.disable_seed_indicator,
        seed_curve_amplify_min=args.seed_curve_amplify_min,
        seed_curve_amplify_max=args.seed_curve_amplify_max,
        random_seed=args.random_seed,
    )

    model_input_dim = int(dataset.input_dim)

    model = GNNRNNForecastModel(
        num_nodes=dataset.num_nodes,
        input_dim=model_input_dim,
        hidden_dim=args.hidden_dim,
        horizon=args.horizon,
        rnn_type=args.rnn_type,
        rnn_layers=args.rnn_layers,
        gat_heads=args.gat_heads,
    ).to(device)

    edge_index = artifacts.edge_index.to(device)
    edge_weight = artifacts.edge_weight.to(device)

    criterion = nn.MSELoss().to(device)
    optimizer = optim.AdamW(
        model.parameters(), lr=args.lr, weight_decay=args.weight_decay
    )

    best_val = float("inf")
    best_state: Dict[str, torch.Tensor] | None = None
    no_improve_epochs = 0
    patience = max(0, int(args.early_stopping_patience))
    min_delta = max(0.0, float(args.early_stopping_min_delta))

    for epoch in range(1, args.epochs + 1):
        model.train()
        train_losses = []

        for x, y in train_loader:
            x = x.to(device)
            y = y.to(device)

            optimizer.zero_grad()
            pred = model(x, edge_index, edge_weight)
            loss = criterion(pred, y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_losses.append(loss.item())

        train_loss = float(np.mean(train_losses)) if train_losses else float("nan")
        val_loss = _evaluate(model, val_loader, edge_index, edge_weight, criterion, device)

        print(
            f"Epoch {epoch:03d}/{args.epochs} | "
            f"train_mse={train_loss:.6f} | val_mse={val_loss:.6f}"
        )

        improved = np.isfinite(val_loss) and (best_val - val_loss) > min_delta
        if improved:
            best_val = val_loss
            best_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
            no_improve_epochs = 0
        else:
            no_improve_epochs += 1

        if patience > 0 and no_improve_epochs >= patience:
            print(
                "Early stopping triggered at "
                f"epoch {epoch}: no val_mse improvement > {min_delta:.6g} "
                f"for {patience} epoch(s)."
            )
            break

    if best_state is None:
        best_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}

    payload = {
        "model_state_dict": best_state,
        "config": {
            "seq_len": args.seq_len,
            "horizon": args.horizon,
            "hidden_dim": args.hidden_dim,
            "rnn_type": args.rnn_type,
            "rnn_layers": args.rnn_layers,
            "gat_heads": args.gat_heads,
            "input_dim": model_input_dim,
            "num_nodes": int(dataset.num_nodes),
            "outbreak_aug_prob": float(args.outbreak_aug_prob),
            "outbreak_baseline_max": float(args.outbreak_baseline_max),
            "use_seed_indicator": bool(not args.disable_seed_indicator),
            "seed_curve_amplify_min": float(args.seed_curve_amplify_min),
            "seed_curve_amplify_max": float(args.seed_curve_amplify_max),
            "random_seed": int(args.random_seed),
        },
        "artifacts": {
            "countries": artifacts.countries,
            "country_to_idx": artifacts.country_to_idx,
            "code_to_name": artifacts.code_to_name,
            "name_to_code": artifacts.name_to_code,
            "static_features": artifacts.static_features.cpu(),
            "edge_index": artifacts.edge_index.cpu(),
            "edge_weight": artifacts.edge_weight.cpu(),
            "adjacency": artifacts.adjacency.cpu(),
        },
        "best_val_loss": best_val,
    }

    torch.save(payload, ckpt_path)
    print(f"Saved checkpoint: {ckpt_path}")

    summary_path = ckpt_path.with_suffix(".json")
    summary_path.write_text(
        json.dumps(
            {
                "checkpoint": str(ckpt_path),
                "best_val_loss": best_val,
                "num_countries": len(artifacts.countries),
                "horizon": args.horizon,
                "seq_len": args.seq_len,
                "rnn_type": args.rnn_type,
                "distance_threshold_km": args.distance_threshold,
                "kernel_scale_km": args.kernel_scale,
                "density_exponent": args.density_exponent,
                "graph_top_k": args.graph_top_k,
                "early_stopping_patience": args.early_stopping_patience,
                "early_stopping_min_delta": args.early_stopping_min_delta,
                "outbreak_aug_prob": args.outbreak_aug_prob,
                "outbreak_baseline_max": args.outbreak_baseline_max,
                "use_seed_indicator": not args.disable_seed_indicator,
                "seed_curve_amplify_min": args.seed_curve_amplify_min,
                "seed_curve_amplify_max": args.seed_curve_amplify_max,
                "random_seed": args.random_seed,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Saved summary: {summary_path}")


if __name__ == "__main__":
    train()
