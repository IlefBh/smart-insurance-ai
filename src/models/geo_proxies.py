# src/models/geo_proxies.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, Optional

import pandas as pd


@dataclass
class GeoProxyStore:
    by_governorate: Dict[str, Tuple[float, float]]  # gov -> (density, poi)
    global_fallback: Tuple[float, float]


class GeoProxies:
    """
    Deterministic geo proxies extracted from the dataset:
    - density_per_km2 median per governorate
    - poi_per_km2 median per governorate
    If governorate unknown: global median fallback.
    """

    def __init__(self, data_path: Path = Path("data/processed/business_df_with_governorate.csv")):
        self.data_path = data_path
        self._store: Optional[GeoProxyStore] = None

    def load(self) -> GeoProxyStore:
        if self._store is not None:
            return self._store

        df = pd.read_csv(self.data_path)

        if "density_per_km2" not in df.columns or "poi_per_km2" not in df.columns:
            # hard fallback if columns don't exist
            self._store = GeoProxyStore(by_governorate={}, global_fallback=(1500.0, 60.0))
            return self._store

        # global medians
        g_density = float(df["density_per_km2"].median())
        g_poi = float(df["poi_per_km2"].median())

        by: Dict[str, Tuple[float, float]] = {}
        if "governorate" in df.columns:
            grp = df.groupby("governorate")[["density_per_km2", "poi_per_km2"]].median().reset_index()
            for _, row in grp.iterrows():
                gov = str(row["governorate"])
                by[gov] = (float(row["density_per_km2"]), float(row["poi_per_km2"]))

        self._store = GeoProxyStore(by_governorate=by, global_fallback=(g_density, g_poi))
        return self._store

    def get(self, governorate: str) -> Tuple[float, float]:
        store = self.load()
        if governorate in store.by_governorate:
            return store.by_governorate[governorate]
        return store.global_fallback
