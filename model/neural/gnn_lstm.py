from typing import Literal

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATConv


class GNNRNNForecastModel(nn.Module):
    """GATConv (directed, gated attention) + LSTM/GRU  hybrid forecasting model.

    Improvements over the previous GCNConv version:
    1. GATConv natively supports **directed** graphs — it only aggregates from
       incoming neighbours, so information flows along edge direction.
    2. Multi-head attention learns *which* neighbours matter most at each time
       step, acting as a soft gating mechanism.
    3. Edge weights are incorporated as additional bias in the attention score,
       preserving the gravity-model prior while still being learnable.
    """

    def __init__(
        self,
        num_nodes: int,
        input_dim: int,
        hidden_dim: int,
        horizon: int,
        rnn_type: Literal["lstm", "gru"] = "lstm",
        rnn_layers: int = 1,
        gat_heads: int = 4,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.num_nodes = num_nodes
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.horizon = horizon
        self.rnn_type = rnn_type.lower()

        # GATConv: multi-head, concat=True  => output dim = hidden_dim
        # So per-head dim = hidden_dim // gat_heads
        assert hidden_dim % gat_heads == 0, \
            f"hidden_dim ({hidden_dim}) must be divisible by gat_heads ({gat_heads})"
        self.gat = GATConv(
            in_channels=input_dim,
            out_channels=hidden_dim // gat_heads,
            heads=gat_heads,
            concat=True,
            dropout=dropout,
            edge_dim=1,          # accept scalar edge weights
            add_self_loops=False,  # we already have explicit self-loops in adjacency
        )

        rnn_cls = nn.LSTM if self.rnn_type == "lstm" else nn.GRU
        self.rnn = rnn_cls(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=rnn_layers,
            batch_first=True,
            dropout=dropout if rnn_layers > 1 else 0.0,
        )

        self.head = nn.Sequential(
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, horizon),
        )

    def _batch_edge_index(
        self,
        edge_index: torch.Tensor,
        edge_weight: torch.Tensor,
        batch_size: int,
        num_nodes: int,
        device: torch.device,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        offsets = torch.arange(batch_size, device=device, dtype=torch.long) * num_nodes
        offsets = offsets.view(batch_size, 1, 1)

        edge_index_expanded = edge_index.to(device).unsqueeze(0).repeat(batch_size, 1, 1)
        edge_index_expanded = edge_index_expanded + offsets
        edge_index_batched = edge_index_expanded.permute(1, 0, 2).reshape(2, -1)

        edge_weight_batched = edge_weight.to(device).repeat(batch_size)
        return edge_index_batched, edge_weight_batched

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_weight: torch.Tensor,
    ) -> torch.Tensor:
        # x: (batch_size, num_nodes, seq_len, input_dim)
        batch_size, num_nodes, seq_len, _ = x.shape
        device = x.device

        edge_index_batched, edge_weight_batched = self._batch_edge_index(
            edge_index=edge_index,
            edge_weight=edge_weight,
            batch_size=batch_size,
            num_nodes=num_nodes,
            device=device,
        )

        # GATConv expects edge_attr with shape (num_edges, edge_dim)
        edge_attr = edge_weight_batched.unsqueeze(-1)  # (E, 1)

        gnn_seq = []
        for t in range(seq_len):
            xt = x[:, :, t, :].reshape(batch_size * num_nodes, -1)
            ht = self.gat(xt, edge_index_batched, edge_attr=edge_attr)
            ht = F.elu(ht)
            ht = ht.view(batch_size, num_nodes, self.hidden_dim)
            gnn_seq.append(ht)

        # (batch_size, num_nodes, seq_len, hidden_dim)
        gnn_seq = torch.stack(gnn_seq, dim=2)

        # RNN applied independently for each country over time.
        rnn_in = gnn_seq.reshape(batch_size * num_nodes, seq_len, self.hidden_dim)
        rnn_out, _ = self.rnn(rnn_in)
        last_hidden = rnn_out[:, -1, :]

        pred = self.head(last_hidden)
        pred = pred.view(batch_size, num_nodes, self.horizon)
        return pred
