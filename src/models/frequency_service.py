# src/models/frequency_service.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import joblib

from src.models.frequency_model import FrequencyMeta, make_feature_row, predict_p_claim


@dataclass
class FrequencyArtifacts:
    pipeline: Any
    meta: FrequencyMeta


class FrequencyService:
    def __init__(self, artifacts_dir: Path = Path("artifacts/frequency_logreg_calibrated")):
        self.artifacts_dir = artifacts_dir
        self._art: Optional[FrequencyArtifacts] = None

    def load(self) -> FrequencyArtifacts:
        if self._art is not None:
            return self._art

        model_path = self.artifacts_dir / "model.joblib"
        meta_path = self.artifacts_dir / "meta.json"

        if not model_path.exists() or not meta_path.exists():
            raise FileNotFoundError(
                f"Missing frequency artifacts in {self.artifacts_dir}. "
                "Run: python -m scripts.train_frequency_calibrated"
            )

        pipe = joblib.load(model_path)
        meta_dict = json.loads(meta_path.read_text(encoding="utf-8"))
        meta = FrequencyMeta(**meta_dict)

        self._art = FrequencyArtifacts(pipeline=pipe, meta=meta)
        return self._art

    def predict(self, profile: Dict[str, Any]) -> float:
        art = self.load()
        x_df = make_feature_row(profile, art.meta)
        p = predict_p_claim(art.pipeline, x_df)
        print("DEBUG p_claim_from_model:", p)
        return p

