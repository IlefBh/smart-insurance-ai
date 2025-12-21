# scripts/test_severity.py
# Purpose: sanity check for the severity (claim cost) model

import joblib
import pandas as pd

MODEL_PATH = "artifacts/sklearn/severity_model.joblib"


def main():
    # 1️⃣ Load severity model
    model = joblib.load(MODEL_PATH)
    print("✅ Severity model loaded")

    # 2️⃣ Create ONE realistic merchant profile
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

    # 3️⃣ Predict expected claim cost (conditional on a claim)
    expected_cost = float(model.predict(X)[0])

    # 4️⃣ Print result
    print("\n--- Severity prediction ---")
    print(f"Expected claim cost = {expected_cost:.2f} TND")

    # 5️⃣ Sanity checks
    assert expected_cost > 0, "❌ Severity must be positive"

    print("\n✅ Severity model test PASSED")


if __name__ == "__main__":
    main()