

import json
import os
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import joblib

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import GammaRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.features.schemas import (
    SEGMENTATION_FEATURES,
    SEGMENTATION_CAT_COLS,
    SEGMENTATION_NUM_COLS,
    SEGMENTATION_BOOL_COLS,
)

ARTIFACT_DIR = "artifacts/sklearn"
MODEL_PATH = os.path.join(ARTIFACT_DIR, "severity_model.joblib")
METRICS_PATH = os.path.join(ARTIFACT_DIR, "severity_metrics.json")


def build_preprocessor() -> ColumnTransformer:
    numeric_cols = SEGMENTATION_NUM_COLS + SEGMENTATION_BOOL_COLS

    num_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    cat_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("num", num_pipe, numeric_cols),
            ("cat", cat_pipe, SEGMENTATION_CAT_COLS),
        ],
        remainder="drop",
    )


def train_severity(
    df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[Pipeline, Dict]:
    """
    Train GammaRegressor on claim_cost_tnd | claim_occurred=1
    """
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    # 🔴 IMPORTANT: keep only claims
    df_sev = df[df["claim_occurred"] == 1].copy()

    X = df_sev[SEGMENTATION_FEATURES].copy()
    y = df_sev["claim_cost_tnd"].astype(float).values

    # Safety: remove non-positive costs
    mask = y > 0
    X = X.loc[mask]
    y = y[mask]

    # Booleans to 0/1
    X[SEGMENTATION_BOOL_COLS] = X[SEGMENTATION_BOOL_COLS].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=test_size,
        random_state=random_state,
    )

    pre = build_preprocessor()

    model = Pipeline(
        steps=[
            ("preprocess", pre),
            ("glm", GammaRegressor(alpha=1.0, max_iter=1000)),
        ]
    )

    model.fit(X_train, y_train)

    # Evaluation
    y_pred = model.predict(X_test)
    mse =mean_squared_error(y_test, y_pred)
    rmse = mse**0.5

    metrics = {
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "mean_observed_cost": float(np.mean(y_test)),
        "mean_predicted_cost": float(np.mean(y_pred)),
        "mae": float(mean_absolute_error(y_test, y_pred)) ,
        "rmse": float(rmse),
    }

    # Save artifacts
    joblib.dump(model, MODEL_PATH)
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    return model, metrics


def load_severity_model() -> Pipeline:
    return joblib.load(MODEL_PATH)
