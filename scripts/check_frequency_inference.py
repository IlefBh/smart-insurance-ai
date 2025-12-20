# scripts/check_frequency_inference.py
from __future__ import annotations

from src.models.frequency_service import FrequencyService


def main():
    svc = FrequencyService()

    samples = [
    {
        "governorate": "Tunis",
        "activity_type": "grocery",
        "density_per_km2": 4000,
        "poi_per_km2": 150,
        "years_active": 8,
        "shop_area_m2": 40,
        "assets_value_tnd": 60000,
        "revenue_monthly_tnd": 8000,
        "open_at_night": False,
        "security_alarm": True,
        "security_camera": True,
        "fire_extinguisher": True,
    },
    {
        "governorate": "Tunis",
        "activity_type": "grocery",
        "density_per_km2": 4000,
        "poi_per_km2": 150,
        "years_active": 0,
        "shop_area_m2": 40,
        "assets_value_tnd": 60000,
        "revenue_monthly_tnd": 8000,
        "open_at_night": True,
        "security_alarm": False,
        "security_camera": False,
        "fire_extinguisher": True,
    },
]

    print("=== Frequency sanity-check ===")
    for i, p in enumerate(samples, 1):
        p_claim = svc.predict(p)
        print(f"Sample {i}: p_claim={p_claim:.3f}")


if __name__ == "__main__":
    main()
