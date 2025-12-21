# src/models/segmentation_runtime.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import pandas as pd

# Keep same artifact paths as training
ARTIFACT_DIR = Path("artifacts/sklearn")
PIPELINE_PATH = ARTIFACT_DIR / "segmentation_pipeline.joblib"
PROFILES_PATH = ARTIFACT_DIR / "cluster_profiles.json"


def predict_cluster_id(profile: Dict[str, Any]) -> int:
    """
    Runtime-only: predict cluster_id using the saved pipeline.
    If artifacts missing, return 0 so API can still run.
    """
    if not PIPELINE_PATH.exists():
        return 0

    pipe = joblib.load(PIPELINE_PATH)
    X = pd.DataFrame([profile])
    return int(pipe.predict(X)[0])


def cluster_to_template_hint(cluster_id: int) -> Optional[str]:
    """
    Runtime-only: return recommended_product from cluster profiles (if available).
    """
    if not PROFILES_PATH.exists():
        return None

    profiles = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    for c in profiles.get("clusters", []):
        if int(c.get("cluster_id", -1)) == int(cluster_id):
            return c.get("recommended_product")
    return None
