"""TCN-based epidemic spread prediction model.

Architecture:
- Shared TCN encoder processes each country's time series independently
- Cross-country mixing layer captures inter-country dependencies
- Per-country output head predicts future new_cases_smoothed
"""

import torch
import torch.nn as nn


class CausalConv1d(nn.Module):
    """1D causal convolution with left-padding so output[t] depends only on input[<=t]."""

    def __init__(self, in_channels, out_channels, kernel_size, dilation=1):
        super().__init__()
        self.padding = (kernel_size - 1) * dilation
        self.conv = nn.Conv1d(
            in_channels, out_channels, kernel_size,
            padding=self.padding, dilation=dilation,
        )

    def forward(self, x):
        # x: (batch, channels, seq_len)
        out = self.conv(x)
        if self.padding > 0:
            out = out[:, :, :-self.padding]
        return out


class TemporalBlock(nn.Module):
    """TCN residual block: dilated causal conv -> ReLU -> dropout -> dilated causal conv -> ReLU -> dropout + residual."""

    def __init__(self, in_channels, out_channels, kernel_size, dilation, dropout=0.2):
        super().__init__()
        self.conv1 = CausalConv1d(in_channels, out_channels, kernel_size, dilation)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(dropout)
        self.conv2 = CausalConv1d(out_channels, out_channels, kernel_size, dilation)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(dropout)
        self.downsample = nn.Conv1d(in_channels, out_channels, 1) if in_channels != out_channels else None
        self.relu = nn.ReLU()

    def forward(self, x):
        out = self.conv1(x)
        out = self.relu1(out)
        out = self.dropout1(out)
        out = self.conv2(out)
        out = self.relu2(out)
        out = self.dropout2(out)
        res = x if self.downsample is None else self.downsample(x)
        return self.relu(out + res)


class EpidemicTCN(nn.Module):
    """Multi-country epidemic forecast model.

    Processes each country's history through a shared TCN, then mixes across
    countries to capture spread dynamics, and outputs per-country predictions.
    """

    def __init__(
        self,
        num_countries: int,
        num_dynamic_features: int,
        num_static_features: int,
        history_days: int = 14,
        forecast_days: int = 30,
        hidden_size: int = 128,
        num_levels: int = 3,
        kernel_size: int = 3,
        dropout: float = 0.2,
        use_country_embedding: bool = True,
        country_embedding_dim: int = 32,
    ):
        super().__init__()
        self.num_countries = num_countries
        self.num_dynamic_features = num_dynamic_features
        self.num_static_features = num_static_features
        self.history_days = history_days
        self.forecast_days = forecast_days
        self.hidden_size = hidden_size
        self.use_country_embedding = use_country_embedding

        total_in_features = num_dynamic_features + num_static_features + 1  # +1 for is_origin flag

        if use_country_embedding:
            self.country_embedding = nn.Embedding(num_countries, country_embedding_dim)
            total_in_features += country_embedding_dim

        # TCN layers with increasing dilation
        layers = []
        in_ch = total_in_features
        for i in range(num_levels):
            dilation = 2 ** i
            out_ch = hidden_size if i == 0 else hidden_size
            layers.append(
                TemporalBlock(in_ch, out_ch, kernel_size, dilation, dropout)
            )
            in_ch = out_ch
        self.tcn = nn.Sequential(*layers)

        # Global context + per-country output head
        # After TCN: each country gets encoded to (hidden_size,)
        # Global pooling (mean+max) captures cross-country dynamics efficiently
        # Static features are also fed directly to the output head for per-country differentiation
        self.global_context_dim = hidden_size * 2  # mean+max pooling
        head_input_dim = hidden_size + self.global_context_dim + num_static_features + 1  # +1 for origin flag

        self.output_head = nn.Sequential(
            nn.Linear(head_input_dim, hidden_size * 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size * 2, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, forecast_days),
        )

    def forward(self, dynamic_features, static_features, origin_mask, country_ids=None):
        """
        Args:
            dynamic_features: (batch, num_countries, history_days, num_dynamic_features)
            static_features:  (batch, num_countries, num_static_features)
            origin_mask:       (batch, num_countries, 1) - 1 for origin country
            country_ids:       (batch, num_countries) - optional country indices for embedding

        Returns:
            (batch, num_countries, forecast_days) - predicted new_cases_smoothed
        """
        batch_size = dynamic_features.size(0)
        n_countries = dynamic_features.size(1)

        # Expand static features and origin mask along time dimension
        static_expanded = static_features.unsqueeze(2).expand(-1, -1, self.history_days, -1)
        origin_expanded = origin_mask.unsqueeze(2).expand(-1, -1, self.history_days, 1)

        # Concatenate all input features
        combined = torch.cat([dynamic_features, static_expanded, origin_expanded], dim=-1)

        # Add country embedding if enabled
        if self.use_country_embedding and country_ids is not None:
            country_emb = self.country_embedding(country_ids)
            country_emb = country_emb.unsqueeze(2).expand(-1, -1, self.history_days, -1)
            combined = torch.cat([combined, country_emb], dim=-1)

        # Reshape to (batch * num_countries, features, history_days) for TCN
        combined = combined.view(batch_size * n_countries, -1, self.history_days)

        # TCN encoding
        encoded = self.tcn(combined)  # (B*N, hidden, history_days)
        encoded = encoded[:, :, -1]   # take last time step: (B*N, hidden)

        # Reshape to (B, N, hidden)
        encoded = encoded.view(batch_size, n_countries, self.hidden_size)

        # Global context via mean+max pooling across countries
        global_mean = encoded.mean(dim=1)  # (B, hidden)
        global_max = encoded.max(dim=1).values  # (B, hidden)
        global_context = torch.cat([global_mean, global_max], dim=-1)  # (B, 2*hidden)

        # For each country: concat country encoding + global context + static features + origin flag
        global_expanded = global_context.unsqueeze(1).expand(-1, n_countries, -1)  # (B, N, 2*hidden)
        origin_flat = origin_mask.squeeze(-1).unsqueeze(-1).expand(-1, -1, 1)  # (B, N, 1)

        per_country_input = torch.cat([encoded, global_expanded, static_features, origin_flat], dim=-1)

        # Per-country output
        output = self.output_head(per_country_input)  # (B, N, forecast_days)

        # Softplus to ensure non-negative predictions
        return torch.nn.functional.softplus(output)

    @torch.no_grad()
    def predict(self, dynamic_features, static_features, origin_idx, country_ids):
        """Convenience method for single-sample inference.

        Args:
            dynamic_features: (num_countries, history_days, num_dynamic_features)
            static_features:  (num_countries, num_static_features)
            origin_idx:       int - index of origin country
            country_ids:      (num_countries,) - country embedding indices

        Returns:
            (num_countries, forecast_days) - predicted new_cases_smoothed
        """
        device = next(self.parameters()).device

        dynamic_features = dynamic_features.unsqueeze(0).to(device)
        static_features = static_features.unsqueeze(0).to(device)
        country_ids = country_ids.unsqueeze(0).to(device)

        origin_mask = torch.zeros(1, self.num_countries, 1, device=device)
        origin_mask[0, origin_idx, 0] = 1.0

        output = self.forward(dynamic_features, static_features, origin_mask, country_ids)
        return output.squeeze(0).cpu()
