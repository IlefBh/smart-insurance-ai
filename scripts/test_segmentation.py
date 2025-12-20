# scripts/test_segmentation.py

import json
import joblib
import pandas as pd

PIPELINE_PATH = "artifacts/sklearn/segmentation_pipeline.joblib"
PROFILES_PATH = "artifacts/sklearn/cluster_profiles.json"

def main():
    pipeline = joblib.load(PIPELINE_PATH)
    print("✅ Pipeline loaded")

    # A simple merchant example (edit values if you want)
    sample = {
        "governorate": "Tunis",
        "density_per_km2": 5000,
        "poi_per_km2": 120,
        "years_active": 3,
        "activity_type": "pharmacy",
        "shop_area_m2": 40,
        "assets_value_tnd": 90000,
        "revenue_monthly_tnd": 12000,
        "revenue_bucket": "high",
        "open_at_night": 0,
        "security_alarm": 1,
        "security_camera": 1,
        "fire_extinguisher": 1,
    }

    X = pd.DataFrame([sample])
    cluster_id = int(pipeline.predict(X)[0])
    print("✅ Predicted cluster_id:", cluster_id)

    with open(PROFILES_PATH, "r", encoding="utf-8") as f:
        profiles = json.load(f)

    clusters = profiles.get("clusters", [])
    entry = next((c for c in clusters if int(c.get("cluster_id")) == cluster_id), None)

    if not entry:
        print("❌ Cluster id not found in cluster_profiles.json")
        return

    print("✅ label:", entry.get("label"))
    print("✅ recommended_product:", entry.get("recommended_product"))
    print("✅ underwriting_flag:", entry.get("underwriting_flag"))
    print("✅ risk_profile:", entry.get("risk_profile"))

if __name__ == "__main__":
    main()
