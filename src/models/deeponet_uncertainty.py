# src/models/deeponet_uncertainty.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import torch
import torch.nn as nn


class MLP(nn.Module):
    def __init__(self, in_dim: int, hidden: int = 128, out_dim: int = 128, dropout: float = 0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, out_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class DeepONetUncertainty(nn.Module):
    """
    DeepONet minimal (hackathon-grade):

    - Branch net: encode merchant features x
    - Trunk net:  encode context t (ex: quantiles assets/revenue)
    - Output: sigmoid( <branch(x), trunk(t)> ) -> uncertainty_score in [0, 1]
    """
    def __init__(
        self,
        x_dim: int,
        t_dim: int = 2,
        latent_dim: int = 128,
        hidden: int = 128,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.branch = MLP(x_dim, hidden=hidden, out_dim=latent_dim, dropout=dropout)
        self.trunk = MLP(t_dim, hidden=hidden, out_dim=latent_dim, dropout=dropout)
        self.bias = nn.Parameter(torch.zeros(1))

    def forward(self, x: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
        bx = self.branch(x)  # (B, latent_dim)
        tt = self.trunk(t)   # (B, latent_dim)
        dot = (bx * tt).sum(dim=1, keepdim=True) + self.bias  # (B, 1)
        return torch.sigmoid(dot)  # (B, 1)


@dataclass
class InferenceResult:
    uncertainty_score: float
    uncertainty_band: str


def band_from_score(score: float) -> str:
    # Seuils déterministes et auditables
    if score >= 0.70:
        return "HIGH"
    if score >= 0.40:
        return "MEDIUM"
    return "LOW"


@torch.no_grad()
def predict_uncertainty(
    model: DeepONetUncertainty,
    x: torch.Tensor,
    t: torch.Tensor,
    device: Optional[str] = None,
) -> InferenceResult:
    model.eval()
    if device:
        model.to(device)
        x = x.to(device)
        t = t.to(device)

    y = model(x, t).detach().cpu().numpy().reshape(-1)
    score = float(y[0])
    return InferenceResult(uncertainty_score=score, uncertainty_band=band_from_score(score))
