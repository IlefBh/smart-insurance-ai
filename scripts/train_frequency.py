# scripts/train_frequency.py
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss

from src.models.frequency_model import (
    FrequencyMeta,
    build_frequency_preprocessor,
    build_frequency_model,
)

ART_DIR = Path("artifacts/frequency_logreg")
DATA_PATH = Path("data/processed/business_df_with_governorate.csv")


def main():
    ART_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DATA_PATH)

    # Target
    if "claim_occurred" not in df.columns:
        raise ValueError("Expected target column 'claim_occurred' not found in dataset.")

    # Meta (features used by the model)
    meta = FrequencyMeta(
        model="LogisticRegressionFrequency",
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

    # Clean minimal (no data mutation; just safe fills inside training)
    X = df[meta.features_num + meta.features_cat + meta.features_bool].copy()
    y = df[meta.target].astype(int)

    # Ensure bool columns are 0/1
    for b in meta.features_bool:
        X[b] = X[b].astype(bool)

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    pre = build_frequency_preprocessor(meta)
    clf = build_frequency_model(random_state=42)

    pipe = Pipeline([("preprocessor", pre), ("clf", clf)])
    pipe.fit(X_train, y_train)

    # Eval
    val_proba = pipe.predict_proba(X_val)[:, 1]
    roc = roc_auc_score(y_val, val_proba)
    ap = average_precision_score(y_val, val_proba)
    brier = brier_score_loss(y_val, val_proba)

    metrics = {
        "roc_auc": float(roc),
        "avg_precision": float(ap),
        "brier": float(brier),
        "n_train": int(len(X_train)),
        "n_val": int(len(X_val)),
        "positive_rate_train": float(np.mean(y_train)),
        "positive_rate_val": float(np.mean(y_val)),
    }

    # Save artifacts
    joblib.dump(pipe, ART_DIR / "model.joblib")
    (ART_DIR / "meta.json").write_text(json.dumps(meta.__dict__, indent=2), encoding="utf-8")
    (ART_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("=== Frequency model trained ===")
    print("Artifacts:", ART_DIR)
    print("Metrics:", json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
