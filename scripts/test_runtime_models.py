# scripts/test_runtime_models.py
from __future__ import annotations

import pandas as pd

from src.models.segmentation_runtime import predict_cluster_id, cluster_to_template_hint
from src.models.frequency import load_frequency_model, predict_p_claim


def main():
    profile = {
        "governorate": "Tunis",
        "density_per_km2": 5000,
        "poi_per_km2": 120,
        "years_active": 5,
        "activity_type": "grocery",
        "shop_area_m2": 40,
        "assets_value_tnd": 60000,
        "revenue_monthly_tnd": 8000,
        "revenue_bucket": "medium",
        "open_at_night": 0,
        "security_alarm": 1,
        "security_camera": 1,
        "fire_extinguisher": 1,
    }

    cid = predict_cluster_id(profile)
    hint = cluster_to_template_hint(cid)

    freq_model = load_frequency_model()
    X = pd.DataFrame([profile])
    p = predict_p_claim(freq_model, X)

    print("cluster_id:", cid)
    print("template_hint:", hint)
    print("p_claim:", p)


if __name__ == "__main__":
    main()
