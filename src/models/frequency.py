# src/models/frequency.py

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
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
)

from src.features.schemas import (
    SEGMENTATION_FEATURES,       # reuse same X list (good consistency)
    SEGMENTATION_CAT_COLS,
    SEGMENTATION_NUM_COLS,
    SEGMENTATION_BOOL_COLS,
)

ARTIFACT_DIR = "artifacts/sklearn"
MODEL_PATH = os.path.join(ARTIFACT_DIR, "frequency_model.joblib")
METRICS_PATH = os.path.join(ARTIFACT_DIR, "frequency_metrics.json")


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


def train_frequency(
    df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[Pipeline, Dict]:
    """
    Train claim frequency model: LogisticRegression with class_weight balanced.
    Saves model + metrics.
    """
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    # X and y
    X = df[SEGMENTATION_FEATURES].copy()
    y = df["claim_occurred"].astype(int).values

    # bools to 0/1
    X[SEGMENTATION_BOOL_COLS] = X[SEGMENTATION_BOOL_COLS].astype(int)

    # train/test split (stratify keeps same 0/1 rate)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )

    pre = build_preprocessor()

    clf = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        solver="lbfgs",
    )

    model = Pipeline(
        steps=[
            ("preprocess", pre),
            ("clf", clf),
        ]
    )

    model.fit(X_train, y_train)

    # Evaluate
    proba_test = model.predict_proba(X_test)[:, 1]
    pred_test = (proba_test >= 0.5).astype(int)

    metrics = {
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "positive_rate_train": float(np.mean(y_train)),
        "positive_rate_test": float(np.mean(y_test)),
        "roc_auc": float(roc_auc_score(y_test, proba_test)),
        "pr_auc": float(average_precision_score(y_test, proba_test)),
        "brier": float(brier_score_loss(y_test, proba_test)),
        "confusion_matrix_0_5": confusion_matrix(y_test, pred_test).tolist(),
    }

    # Save
    joblib.dump(model, MODEL_PATH)
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    print("✅ Saved frequency model:", MODEL_PATH)
    print("✅ Saved frequency metrics:", METRICS_PATH)

    return model, metrics


def load_frequency_model() -> Pipeline:
    return joblib.load(MODEL_PATH)


def predict_p_claim(model: Pipeline, profile_df: pd.DataFrame) -> float:
    """
    profile_df: DataFrame with one row and same columns as SEGMENTATION_FEATURES.
    returns p_claim in [0,1]
    """
    return float(model.predict_proba(profile_df)[:, 1][0])
