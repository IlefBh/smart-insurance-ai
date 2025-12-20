# src/models/segmentation.py

import json
import os
from typing import Dict, Tuple, List, Any

import numpy as np
import pandas as pd
import joblib

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from src.features.schemas import (
    SEGMENTATION_FEATURES,
    SEGMENTATION_CAT_COLS,
    SEGMENTATION_NUM_COLS,
    SEGMENTATION_BOOL_COLS,
)

# =========================
# Artifact paths
# =========================
ARTIFACT_DIR = "artifacts/sklearn"
PIPELINE_PATH = os.path.join(ARTIFACT_DIR, "segmentation_pipeline.joblib")
CLUSTERS_PATH = os.path.join(ARTIFACT_DIR, "segmentation_clusters.csv")
PROFILES_PATH = os.path.join(ARTIFACT_DIR, "cluster_profiles.json")


# =========================
# Preprocessing
# =========================
def build_preprocessor() -> ColumnTransformer:
    numeric_cols = SEGMENTATION_NUM_COLS + SEGMENTATION_BOOL_COLS

    numeric_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipe, numeric_cols),
            ("cat", categorical_pipe, SEGMENTATION_CAT_COLS),
        ],
        remainder="drop",
    )


# =========================
# K selection
# =========================
def choose_k_by_silhouette(
    X_transformed,
    k_min: int = 2,
    k_max: int = 10,
) -> Tuple[int, Dict[int, float]]:
    scores: Dict[int, float] = {}
    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init="auto", max_iter=300)
        labels = km.fit_predict(X_transformed)
        scores[k] = float(silhouette_score(X_transformed, labels))

    best_k = max(scores, key=scores.get)
    return best_k, scores


# =========================
# Cluster labeling (business naming)
# =========================
def _as_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def label_and_recommend(cluster: dict, global_medians: dict) -> Dict[str, Any]:
    """
    Deterministic mapping cluster -> (label, recommended_product, underwriting_flag)
    Uses only descriptive stats from the cluster profile (safe, explainable).
    """

    night_rate = _as_float(cluster["security_rates"].get("open_at_night", 0.0))
    alarm_rate = _as_float(cluster["security_rates"].get("security_alarm", 0.0))
    camera_rate = _as_float(cluster["security_rates"].get("security_camera", 0.0))
    ext_rate = _as_float(cluster["security_rates"].get("fire_extinguisher", 0.0))

    assets_med = _as_float(cluster["numeric_summary"]["assets_value_tnd"]["median"])
    years_med = _as_float(cluster["numeric_summary"]["years_active"]["median"])

    g_assets = _as_float(global_medians.get("assets_value_tnd", 0.0))
    g_years = _as_float(global_medians.get("years_active", 0.0))

    security_score = alarm_rate + camera_rate + ext_rate  # 0..3

    # Rule 1: Night & low security => Night & Cash Risk
    if night_rate >= 0.60 and security_score <= 1.20:
        return {
            "label": "Night & Cash Risk",
            "recommended_product": "Night & Cash Risk",
            "underwriting_flag": True,
            "risk_profile": "medium-high",
        }

    # Rule 2: High assets exposure => Commerce Plus
    # Use relative threshold vs global median to stay robust
    if g_assets > 0 and assets_med >= 1.25 * g_assets:
        return {
            "label": "Commerce Plus – Forte valeur exposée",
            "recommended_product": "Commerce Plus",
            "underwriting_flag": False,
            "risk_profile": "medium",
        }

    # Rule 3: New businesses (uncertainty) => Essentiel + UW flag
    if g_years > 0 and years_med <= 0.60 * g_years:
        return {
            "label": "Jeune commerce – Incertitude élevée",
            "recommended_product": "Commerce Essentiel",
            "underwriting_flag": True,
            "risk_profile": "medium",
        }

    # Default
    return {
        "label": "Commerce Essentiel – Profil standard",
        "recommended_product": "Commerce Essentiel",
        "underwriting_flag": False,
        "risk_profile": "low-medium",
    }


# =========================
# Build cluster profiles JSON
# =========================
def build_cluster_profiles(df_with_cluster: pd.DataFrame) -> Dict[str, Any]:
    """
    df_with_cluster contains SEGMENTATION_FEATURES + cluster_id
    Returns JSON-ready dict with clusters[] having:
      stats + label + recommended_product + underwriting_flag
    """

    # Global medians used for robust thresholds
    global_medians = {
        "assets_value_tnd": float(df_with_cluster["assets_value_tnd"].median()),
        "years_active": float(df_with_cluster["years_active"].median()),
    }

    n_total = len(df_with_cluster)
    global_means = df_with_cluster.mean(numeric_only=True)

    clusters: List[dict] = []

    for cid in sorted(df_with_cluster["cluster_id"].unique()):
        sub = df_with_cluster[df_with_cluster["cluster_id"] == cid].copy()

        cluster: Dict[str, Any] = {
            "cluster_id": int(cid),
            "size": int(len(sub)),
            "share": float(len(sub) / n_total),
            "numeric_summary": {},
            "categorical_summary": {},
            "security_rates": {},
            "top_drivers": [],
        }

        # Numeric summaries (mean/median)
        for col in SEGMENTATION_NUM_COLS:
            cluster["numeric_summary"][col] = {
                "mean": float(sub[col].mean()),
                "median": float(sub[col].median()),
            }

        # Security / boolean rates
        for col in SEGMENTATION_BOOL_COLS:
            cluster["security_rates"][col] = float(sub[col].mean())

        # Categorical distributions (top 3)
        for col in SEGMENTATION_CAT_COLS:
            vc = sub[col].fillna("UNKNOWN").value_counts(normalize=True).head(3)
            cluster["categorical_summary"][col] = [
                {"value": str(idx), "share": float(val)} for idx, val in vc.items()
            ]

        # Top drivers: relative diff vs global mean (descriptive, not causal)
        drivers = []
        for col in SEGMENTATION_NUM_COLS:
            g = float(global_means[col]) if col in global_means else 0.0
            s = float(sub[col].mean())
            diff = (s - g) / (abs(g) + 1e-6)
            drivers.append((col, float(diff)))

        drivers = sorted(drivers, key=lambda x: abs(x[1]), reverse=True)[:5]
        cluster["top_drivers"] = [{"feature": f, "relative_diff": d} for f, d in drivers]

        # ✅ ADD BUSINESS LABEL + PRODUCT RECOMMENDATION
        naming = label_and_recommend(cluster, global_medians)
        cluster.update(naming)

        clusters.append(cluster)

    return {
        "global_medians": global_medians,
        "clusters": clusters,
    }


# =========================
# Train segmentation (Model 1)
# =========================
def train_segmentation(
    df: pd.DataFrame,
    k_min: int = 2,
    k_max: int = 10,
) -> Tuple[int, Dict[int, float]]:
    """
    Trains segmentation pipeline and saves artifacts.
    Expects df has the columns listed in SEGMENTATION_FEATURES.
    """
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    # X only
    X = df[SEGMENTATION_FEATURES].copy()

    # Ensure bools are 0/1
    X[SEGMENTATION_BOOL_COLS] = X[SEGMENTATION_BOOL_COLS].astype(int)

    preprocessor = build_preprocessor()
    X_transformed = preprocessor.fit_transform(X)

    best_k, silhouette_scores = choose_k_by_silhouette(X_transformed, k_min=k_min, k_max=k_max)

    kmeans = KMeans(n_clusters=best_k, random_state=42, n_init="auto", max_iter=300)

    pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("kmeans", kmeans),
        ]
    )

    pipeline.fit(X)

    # Predict cluster_id for analysis
    out_df = df.copy()
    out_df["cluster_id"] = pipeline.predict(X)

    # Build profiles + labels
    profiles_pack = build_cluster_profiles(out_df)

    profiles_json = {
        "chosen_k": int(best_k),
        "silhouette_scores": {int(k): float(v) for k, v in silhouette_scores.items()},
        **profiles_pack,
    }

    # Save artifacts
    joblib.dump(pipeline, PIPELINE_PATH)
    out_df.to_csv(CLUSTERS_PATH, index=False)

    with open(PROFILES_PATH, "w", encoding="utf-8") as f:
        json.dump(profiles_json, f, ensure_ascii=False, indent=2)

    print("Saved pipeline:", PIPELINE_PATH)
    print("Saved clusters:", CLUSTERS_PATH)
    print("Saved profiles:", PROFILES_PATH)

    return best_k, silhouette_scores