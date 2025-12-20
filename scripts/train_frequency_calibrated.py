# scripts/train_frequency_calibrated.py
from __future__ import annotations

import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss

from src.models.frequency_model import (
    FrequencyMeta,
    build_frequency_preprocessor,
    build_frequency_model,
)

DATA_PATH = Path("data/processed/business_df_with_governorate.csv")
ART_DIR = Path("artifacts/frequency_logreg_calibrated")


def main():
    ART_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATA_PATH)

    if "claim_occurred" not in df.columns:
        raise ValueError("Expected target column 'claim_occurred' not found.")

    meta = FrequencyMeta(
        model="LogisticRegressionFrequencyCalibrated",
        target="claim_occurred",
        features_num=[
            "density_per_km2",
            "poi_per_km2",
            "years_active",
            "shop_area_m2",
            "assets_value_tnd",
            "revenue_monthly_tnd",
        ],
        features_cat=["governorate", "activity_type"],
        features_bool=["open_at_night", "security_alarm", "security_camera", "fire_extinguisher"],
    )

    feat = meta.features_num + meta.features_cat + meta.features_bool
    missing = [c for c in feat if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset missing required columns: {missing}")

    X = df[feat].copy()
    y = df[meta.target].astype(int)

    for b in meta.features_bool:
        X[b] = X[b].astype(bool)

    # Keep a clean hold-out set for final evaluation
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    base_pipe = Pipeline([
        ("preprocessor", build_frequency_preprocessor(meta)),
        ("clf", build_frequency_model(random_state=42)),  # keep your settings (balanced etc.)
    ])

    # Calibrate with internal CV on TRAIN only (no "prefit")
    cal = CalibratedClassifierCV(
        estimator=base_pipe,
        method="sigmoid",
        cv=3,   # robust + compatible
    )
    cal.fit(X_train, y_train)

    # Evaluate on hold-out VAL
    val_proba = cal.predict_proba(X_val)[:, 1]
    metrics = {
        "roc_auc": float(roc_auc_score(y_val, val_proba)),
        "avg_precision": float(average_precision_score(y_val, val_proba)),
        "brier": float(brier_score_loss(y_val, val_proba)),
        "positive_rate_val": float(np.mean(y_val)),
        "n_train": int(len(X_train)),
        "n_val": int(len(X_val)),
    }

    joblib.dump(cal, ART_DIR / "model.joblib")
    (ART_DIR / "meta.json").write_text(json.dumps(meta.__dict__, indent=2), encoding="utf-8")
    (ART_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("=== Frequency calibrated model trained ===")
    print("Artifacts:", ART_DIR)
    print("Metrics:", json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
