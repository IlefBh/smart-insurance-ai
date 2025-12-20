from __future__ import annotations

import pandas as pd
from pathlib import Path
from src.models.frequency_service import FrequencyService
from src.models.frequency_model import predict_p_claim

DATA_PATH = Path("data/processed/business_df_with_governorate.csv")

def main():
    svc = FrequencyService()
    art = svc.load()

    df = pd.read_csv(DATA_PATH)
    # Build X using EXACT same feature names as meta
    cols = art.meta.features_num + art.meta.features_bool + art.meta.features_cat
    X = df[cols].copy()

    # Enforce same typing rules as inference
    for c in art.meta.features_num:
        X[c] = pd.to_numeric(X[c], errors="coerce").fillna(0.0).astype(float)
    for c in art.meta.features_bool:
        X[c] = pd.to_numeric(X[c], errors="coerce").fillna(0).astype(int)
    for c in art.meta.features_cat:
        X[c] = X[c].astype(str).str.strip()

    proba = art.pipeline.predict_proba(X)[:, 1]
    print("=== Artifact audit ===")
    print("min:", float(proba.min()))
    print("mean:", float(proba.mean()))
    print("max:", float(proba.max()))

if __name__ == "__main__":
    main()
