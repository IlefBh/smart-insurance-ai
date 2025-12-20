# scripts/evaluate_frequency_outputs.py
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


DATA_PATH = Path("data/processed/business_df_with_governorate.csv")
ART_DIR = Path("artifacts/frequency_logreg_calibrated")


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    model_path = ART_DIR / "model.joblib"
    meta_path = ART_DIR / "meta.json"
    if not model_path.exists() or not meta_path.exists():
        raise FileNotFoundError(
            f"Frequency artifacts not found in {ART_DIR}. "
            "Run: python -m scripts.train_frequency"
        )

    df = pd.read_csv(DATA_PATH)
    pipe = joblib.load(model_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    features = meta["features_num"] + meta["features_cat"] + meta["features_bool"]
    missing = [c for c in features if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required feature columns: {missing}")

    X = df[features].copy()
    # bool columns as bool
    for b in meta["features_bool"]:
        X[b] = X[b].astype(bool)

    proba = pipe.predict_proba(X)[:, 1].astype(float)

    print("=== Frequency model output distribution (p_claim) ===")
    qs = [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
    for q in qs:
        print(f"p{int(q*100):02d} = {np.quantile(proba, q):.4f}")
    print(f"min={proba.min():.4f} max={proba.max():.4f} mean={proba.mean():.4f}")

    extreme = float(np.mean((proba < 0.05) | (proba > 0.95)))
    print(f"extreme(<0.05 or >0.95): {extreme*100:.2f}%")

    # Optional: compare to base rate
    if "claim_occurred" in df.columns:
        base_rate = float(df["claim_occurred"].astype(int).mean())
        print(f"base_rate(claim_occurred=1): {base_rate:.4f}")


if __name__ == "__main__":
    main()
