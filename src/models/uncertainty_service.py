# src/models/uncertainty_service.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import numpy as np
import pandas as pd
import torch


from src.models.deeponet_uncertainty import DeepONetUncertainty, InferenceResult, predict_uncertainty


@dataclass
class UncertaintyArtifacts:
    model: DeepONetUncertainty
    preprocessor: Any
    meta: Dict[str, Any]
    device: str


class UncertaintyService:
    def __init__(self, artifacts_dir: Path = Path("artifacts/uncertainty_deeponet")):
        self.artifacts_dir = artifacts_dir
        self._art: Optional[UncertaintyArtifacts] = None

    def load(self) -> UncertaintyArtifacts:
        if self._art is not None:
            return self._art

        meta = json.loads((self.artifacts_dir / "meta.json").read_text(encoding="utf-8"))
        x_dim = int(meta["x_dim"])
        device = "cuda" if torch.cuda.is_available() else "cpu"

        preprocessor = joblib.load(self.artifacts_dir / "preprocessor.joblib")

        model = DeepONetUncertainty(x_dim=x_dim, t_dim=2, latent_dim=128, hidden=128, dropout=0.10)
        state = torch.load(self.artifacts_dir / "model.pt", map_location=device)
        model.load_state_dict(state)
        model.to(device)

        self._art = UncertaintyArtifacts(model=model, preprocessor=preprocessor, meta=meta, device=device)
        return self._art

    @staticmethod
    def _build_t_from_profile(profile: Dict[str, Any]) -> np.ndarray:
        """
        Contexte trunk minimal:
          - approx quantiles via normalisation simple (hackathon-grade)
        IMPORTANT: ceci est une approx d'inférence (pas la qcut globale).
        C'est OK car trunk = contexte faible, et l'essentiel est branch(features).

        On mappe assets & revenue sur [0,1] par capping.
        """
        assets = float(profile.get("assets_value_tnd", 0.0))
        revenue = float(profile.get("revenue_monthly_tnd", 0.0))

        # bornes raisonnables pour normaliser sans dépendre du dataset global
        assets_cap = min(max(assets, 0.0), 300000.0) / 300000.0
        revenue_cap = min(max(revenue, 0.0), 200000.0) / 200000.0
        return np.array([[assets_cap, revenue_cap]], dtype=np.float32)

    def predict(self, profile: Dict[str, Any]) -> InferenceResult:
        art = self.load()

        num_cols = art.meta["features_num"]
        cat_cols = art.meta["features_cat"]
        bool_cols = art.meta["features_bool"]

        row: Dict[str, Any] = {}

        # Numériques -> float, défaut 0.0
        for c in num_cols:
            v = profile.get(c, 0.0)
            try:
                row[c] = float(v) if v is not None else 0.0
            except Exception:
                row[c] = 0.0

        # Booléens -> bool, défaut False
        for c in bool_cols:
            v = profile.get(c, False)
            row[c] = bool(v)

        # Catégorielles -> str, défaut "UNKNOWN"
        for c in cat_cols:
            v = profile.get(c, "UNKNOWN")
            row[c] = str(v) if v is not None else "UNKNOWN"

        df = pd.DataFrame([row])

        X_enc = art.preprocessor.transform(df)
        X_arr = X_enc.toarray() if hasattr(X_enc, "toarray") else X_enc

        x_t = torch.tensor(X_arr, dtype=torch.float32)
        t_np = self._build_t_from_profile(profile)
        t_t = torch.tensor(t_np, dtype=torch.float32)

        res = predict_uncertainty(art.model, x_t, t_t, device=art.device)

        # Hardening: never return NaN/inf
        score = float(res.uncertainty_score)
        if not np.isfinite(score):
            # fallback déterministe (audit-friendly)
            return InferenceResult(uncertainty_score=0.50, uncertainty_band="MEDIUM")

        return res

