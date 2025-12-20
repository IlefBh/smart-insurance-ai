# scripts/train_deeponet_uncertainty.py
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
import joblib

import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader

from src.models.deeponet_uncertainty import DeepONetUncertainty


DATA_PATH_DEFAULT = Path("data/processed/business_df_with_governorate.csv")  # tu peux copier ton CSV là
ART_DIR = Path("artifacts/uncertainty_deeponet")


def build_uncertainty_target(df: pd.DataFrame) -> pd.Series:
    """
    IMPORTANT: on ne modifie pas la data.
    On crée une cible 'uncertainty_target' uniquement pour l'entraînement.

    Idée (audit-friendly):
      - volatilité fréquence: var(Bernoulli) = p*(1-p) par groupe
      - volatilité sévérité: std(log1p(cost)) parmi les sinistres par groupe
      - mélange pondéré puis normalisation [0,1]

    Groupes métier (simples, explicables):
      - activity_type
      - open_at_night
      - quantiles assets_value_tnd (5 bins)
      - quantiles revenue_monthly_tnd (5 bins)
    """
    df = df.copy()

    # quantiles (dans le pipeline, pas dans le CSV)
    df["assets_q"] = pd.qcut(df["assets_value_tnd"], q=5, labels=False, duplicates="drop")
    df["rev_q"] = pd.qcut(df["revenue_monthly_tnd"], q=5, labels=False, duplicates="drop")

    group_cols = ["activity_type", "open_at_night", "assets_q", "rev_q"]
    g = df.groupby(group_cols, dropna=False)

    # fréquence: p*(1-p)
    p = g["claim_occurred"].mean()
    freq_var = p * (1 - p)

    # sévérité: std(log1p(claim_cost)) sur claim_occurred=1
    df_claims = df[df["claim_occurred"] == 1].copy()
    df_claims["log_cost"] = np.log1p(df_claims["claim_cost_tnd"].clip(lower=0))
    g2 = df_claims.groupby(group_cols, dropna=False)
    sev_std = g2["log_cost"].std().fillna(0.0)

    # compter nb sinistres par groupe pour fiabilité
    sev_n = g2["log_cost"].count().fillna(0)

    # backoff simple si trop peu de sinistres: shrink sev_std vers global
    global_sev_std = float(df_claims["log_cost"].std()) if len(df_claims) > 0 else 0.0
    min_n = 30
    sev_std_shrunk = (sev_std * (sev_n / (sev_n + min_n))) + (global_sev_std * (min_n / (sev_n + min_n)))

    # align index (group index)
    sev_std_shrunk = sev_std_shrunk.reindex(p.index).fillna(global_sev_std)

    # mélange pondéré (déterministe, explicable)
    w_sev, w_freq = 0.70, 0.30
    raw = w_sev * sev_std_shrunk + w_freq * freq_var

    # normalisation [0,1] (min-max)
    raw_min, raw_max = float(raw.min()), float(raw.max())
    if raw_max - raw_min < 1e-9:
        norm = raw * 0.0
    else:
        norm = (raw - raw_min) / (raw_max - raw_min)

    # remapper vers chaque ligne
    target = df[group_cols].merge(
        norm.rename("uncertainty_target").reset_index(),
        on=group_cols,
        how="left"
    )["uncertainty_target"].fillna(float(norm.mean()))

    return target


def main(data_path: Path = DATA_PATH_DEFAULT):
    df = pd.read_csv(data_path)

    # Features (on ignore revenue_bucket volontairement)
    feature_cols_num = [
        "density_per_km2",
        "poi_per_km2",
        "years_active",
        "shop_area_m2",
        "assets_value_tnd",
        "revenue_monthly_tnd",
    ]
    feature_cols_cat = ["governorate", "activity_type"]
    feature_cols_bool = ["open_at_night", "security_alarm", "security_camera", "fire_extinguisher"]

    # cible entraînement (incertitude)
    y = build_uncertainty_target(df).astype(float).values.reshape(-1, 1)

    # contexte trunk: quantiles assets + revenue (2 dims)
    # On le calcule dans le script (pas dans le CSV)
    assets_q = pd.qcut(df["assets_value_tnd"], q=5, labels=False, duplicates="drop").astype(float)
    rev_q = pd.qcut(df["revenue_monthly_tnd"], q=5, labels=False, duplicates="drop").astype(float)
    # normaliser en [0,1]
    t = np.stack([assets_q / 4.0, rev_q / 4.0], axis=1).astype(np.float32)

    X = df[feature_cols_num + feature_cols_cat + feature_cols_bool].copy()

    # Préprocesseur scikit-learn -> donne un vecteur x prêt pour torch
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), feature_cols_num),
            ("cat", OneHotEncoder(handle_unknown="ignore"), feature_cols_cat),
            ("bool", "passthrough", feature_cols_bool),
        ],
        remainder="drop",
    )

    # Split
    X_train, X_test, t_train, t_test, y_train, y_test = train_test_split(
        X, t, y, test_size=0.20, random_state=42
    )

    # Fit preprocess on train only
    X_train_enc = preprocessor.fit_transform(X_train)
    X_test_enc = preprocessor.transform(X_test)

    # Convert to torch tensors
    device = "cuda" if torch.cuda.is_available() else "cpu"

    X_train_t = torch.tensor(X_train_enc.toarray() if hasattr(X_train_enc, "toarray") else X_train_enc, dtype=torch.float32)
    X_test_t = torch.tensor(X_test_enc.toarray() if hasattr(X_test_enc, "toarray") else X_test_enc, dtype=torch.float32)
    t_train_t = torch.tensor(t_train, dtype=torch.float32)
    t_test_t = torch.tensor(t_test, dtype=torch.float32)
    y_train_t = torch.tensor(y_train, dtype=torch.float32)
    y_test_t = torch.tensor(y_test, dtype=torch.float32)

    train_ds = TensorDataset(X_train_t, t_train_t, y_train_t)
    test_ds = TensorDataset(X_test_t, t_test_t, y_test_t)

    train_loader = DataLoader(train_ds, batch_size=512, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=1024, shuffle=False)

    # Model
    x_dim = X_train_t.shape[1]
    model = DeepONetUncertainty(x_dim=x_dim, t_dim=2, latent_dim=128, hidden=128, dropout=0.10).to(device)

    loss_fn = nn.HuberLoss(delta=0.05)  # robuste (queue lourde)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)

    # Training
    epochs = 15
    for epoch in range(1, epochs + 1):
        model.train()
        train_losses = []
        for xb, tb, yb in train_loader:
            xb, tb, yb = xb.to(device), tb.to(device), yb.to(device)
            opt.zero_grad()
            pred = model(xb, tb)
            loss = loss_fn(pred, yb)
            loss.backward()
            opt.step()
            train_losses.append(loss.item())

        model.eval()
        test_losses = []
        with torch.no_grad():
            for xb, tb, yb in test_loader:
                xb, tb, yb = xb.to(device), tb.to(device), yb.to(device)
                pred = model(xb, tb)
                loss = loss_fn(pred, yb)
                test_losses.append(loss.item())

        print(f"[Epoch {epoch:02d}] train={np.mean(train_losses):.5f} | test={np.mean(test_losses):.5f}")

    # Save artifacts
    ART_DIR.mkdir(parents=True, exist_ok=True)

    torch.save(model.state_dict(), ART_DIR / "model.pt")
    joblib.dump(preprocessor, ART_DIR / "preprocessor.joblib")

    meta = {
        "model": "DeepONetUncertainty",
        "x_dim": int(x_dim),
        "t_dim": 2,
        "features_num": feature_cols_num,
        "features_cat": feature_cols_cat,
        "features_bool": feature_cols_bool,
        "target_definition": "group volatility: 0.70*std(log1p(cost)) + 0.30*p*(1-p), normalized",
        "data_path": str(data_path),
    }
    (ART_DIR / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"\nSaved to: {ART_DIR.resolve()}")


if __name__ == "__main__":
    # Mets ton CSV dans data/processed/ pour que ce soit propre côté repo
    main()
