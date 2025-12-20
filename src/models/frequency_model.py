# src/models/frequency_model.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression


@dataclass(frozen=True)
class FrequencyMeta:
    model: str
    features_num: List[str]
    features_cat: List[str]
    features_bool: List[str]
    target: str


def build_frequency_preprocessor(meta: FrequencyMeta) -> ColumnTransformer:
    num = Pipeline([("scaler", StandardScaler())])
    cat = Pipeline([("ohe", OneHotEncoder(handle_unknown="ignore"))])
    pre = ColumnTransformer(
        transformers=[
            ("num", num, meta.features_num),
            ("cat", cat, meta.features_cat),
            ("bool", "passthrough", meta.features_bool),  # expects 0/1
        ],
        remainder="drop",
        sparse_threshold=0.3,
    )
    return pre


def build_frequency_model(random_state: int = 42) -> LogisticRegression:
    return LogisticRegression(
        solver="lbfgs",
        max_iter=2000,
        class_weight="balanced",
        random_state=random_state,
    )


def _to_float(x: Any) -> float:
    if x is None:
        return 0.0
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)
    if isinstance(x, str):
        s = x.strip().replace(",", ".")
        if s == "":
            return 0.0
        try:
            return float(s)
        except ValueError:
            return 0.0
    return 0.0


def _to_int01_bool(x: Any) -> int:
    """
    Safe bool parsing:
    - bool -> 0/1
    - numbers -> >=0.5 => 1 else 0
    - strings like "false", "0", "non" => 0
    - strings like "true", "1", "oui" => 1
    - unknown => 0 (deterministic)
    """
    if x is None:
        return 0
    if isinstance(x, bool):
        return 1 if x else 0
    if isinstance(x, (int, float, np.integer, np.floating)):
        return 1 if float(x) >= 0.5 else 0
    if isinstance(x, str):
        s = x.strip().lower()
        if s in {"1", "true", "yes", "y", "oui", "vrai"}:
            return 1
        if s in {"0", "false", "no", "n", "non", "faux"}:
            return 0
        # IMPORTANT: never do bool("False") — keep deterministic fallback
        return 0
    return 0


def _to_cat(x: Any) -> str:
    if x is None:
        return "UNKNOWN"
    s = str(x).strip()
    return s if s != "" else "UNKNOWN"


def make_feature_row(profile: Dict[str, Any], meta: FrequencyMeta) -> pd.DataFrame:
    """
    Build a single-row DataFrame aligned with meta features.

    Key guarantees:
    - Strict columns set: num + bool + cat
    - Safe casting (NO truthy-string bug)
    - Deterministic fill (0 / UNKNOWN)
    - Stable column order (helps avoid accidental downstream permutation)
    """
    row: Dict[str, Any] = {}

    for c in meta.features_num:
        row[c] = _to_float(profile.get(c))

    # bool features must be 0/1 (ints), not python bools, not strings
    for c in meta.features_bool:
        row[c] = _to_int01_bool(profile.get(c))

    for c in meta.features_cat:
        row[c] = _to_cat(profile.get(c))

    cols = meta.features_num + meta.features_bool + meta.features_cat
    df = pd.DataFrame([row], columns=cols)

    # enforce dtypes explicitly (regulator-friendly + avoids object drift)
    for c in meta.features_num:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0).astype(float)
    for c in meta.features_bool:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    for c in meta.features_cat:
        df[c] = df[c].astype(str)

    return df


def predict_p_claim(pipeline: Pipeline, x_df: pd.DataFrame) -> float:
    proba = pipeline.predict_proba(x_df)[0, 1]
    return float(np.clip(proba, 0.0, 1.0))
