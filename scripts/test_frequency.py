# scripts/test_frequency.py
# Purpose: simple sanity check for the frequency (claim occurrence) model

import joblib
import pandas as pd

MODEL_PATH = "artifacts/sklearn/frequency_model.joblib"


def main():
    # 1️⃣ Load model
    model = joblib.load(MODEL_PATH)
    print("✅ Frequency model loaded")

    # 2️⃣ Create ONE realistic merchant profile (same schema as training)
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

    # 3️⃣ Predict probability
    proba = model.predict_proba(X)

    p_no_claim = float(proba[0, 0])
    p_claim = float(proba[0, 1])

    # 4️⃣ Print results
    print("\n--- Frequency prediction ---")
    print(f"P(no claim) = {p_no_claim:.4f}")
    print(f"P(claim)    = {p_claim:.4f}")

    # 5️⃣ Sanity checks
    assert 0 <= p_claim <= 1, "❌ p_claim is not a valid probability"
    assert abs(p_no_claim + p_claim - 1) < 1e-6, "❌ Probabilities do not sum to 1"

    print("\n✅ Frequency model test PASSED")

if __name__ == "__main__":
    main()