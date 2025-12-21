# scripts/check_deeponet_inference.py
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch

from src.models.deeponet_uncertainty import DeepONetUncertainty, predict_uncertainty

ART_DIR = Path("artifacts/uncertainty_deeponet")
DATA_PATH = Path("data/processed/business_df_with_governorate.csv")


def build_t_from_df(df: pd.DataFrame) -> np.ndarray:
    """
    Même logique que train:
      - quantiles assets + revenue (2 dims)
      - normalisés [0,1] via /4.0 (car q=5 => labels 0..4)
    """
    assets_q = pd.qcut(df["assets_value_tnd"], q=5, labels=False, duplicates="drop").astype(float)
    rev_q = pd.qcut(df["revenue_monthly_tnd"], q=5, labels=False, duplicates="drop").astype(float)
    t = np.stack([assets_q / 4.0, rev_q / 4.0], axis=1).astype(np.float32)
    return t


def main():
    meta = json.loads((ART_DIR / "meta.json").read_text(encoding="utf-8"))
    x_dim = int(meta["x_dim"])
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Load preprocessor + model
    preprocessor = joblib.load(ART_DIR / "preprocessor.joblib")

    model = DeepONetUncertainty(x_dim=x_dim, t_dim=2, latent_dim=128, hidden=128, dropout=0.10)
    state = torch.load(ART_DIR / "model.pt", map_location=device)
    model.load_state_dict(state)
    model.to(device)
    model.eval()

    # Load dataset
    df = pd.read_csv(DATA_PATH)

    # 3 profils: "LOW-ish", "MEDIUM-ish", "HIGH-ish" (heuristique simple)
    df_sorted = df.copy()

    # Robust: open_at_night may be bool/int
    open_night = df_sorted["open_at_night"].astype(float)

    df_sorted["risk_hint"] = (
        0.4 * open_night
        + 0.3 * (df_sorted["years_active"] <= 2).astype(float)
        + 0.3 * (df_sorted["assets_value_tnd"] > df_sorted["assets_value_tnd"].quantile(0.85)).astype(float)
    )

    low = df_sorted.sort_values("risk_hint", ascending=True).iloc[[0]]
    mid = df_sorted.iloc[[len(df_sorted) // 2]]
    high = df_sorted.sort_values("risk_hint", ascending=False).iloc[[0]]

    samples = pd.concat([low, mid, high], axis=0).reset_index(drop=True)

    # Build t for these samples using same logic
    t_all = build_t_from_df(samples)

    # Build X with same columns as training
    feature_cols_num = meta["features_num"]
    feature_cols_cat = meta["features_cat"]
    feature_cols_bool = meta["features_bool"]

    X = samples[feature_cols_num + feature_cols_cat + feature_cols_bool].copy()

    X_enc = preprocessor.transform(X)
    X_arr = X_enc.toarray() if hasattr(X_enc, "toarray") else X_enc

    print("\n=== DeepONet Uncertainty sanity-check ===")

    with torch.no_grad():
        for i in range(len(samples)):
            x_t = torch.tensor(X_arr[i : i + 1], dtype=torch.float32)
            t_t = torch.tensor(t_all[i : i + 1], dtype=torch.float32)

            res = predict_uncertainty(model, x_t, t_t, device=device)

            row = samples.iloc[i]
            print(f"\nSample {i+1}")
            print(f"  governorate={row['governorate']} | activity_type={row['activity_type']}")
            print(f"  years_active={row['years_active']} | open_at_night={row['open_at_night']}")
            print(f"  assets={row['assets_value_tnd']:.0f} | revenue_monthly={row['revenue_monthly_tnd']:.0f}")
            print(f"  -> uncertainty_score={res.uncertainty_score:.3f} | band={res.uncertainty_band}")

    print("\nOK: if scores are in [0,1] and script prints 3 complete samples, we're good.\n")


if __name__ == "__main__":
    main()
