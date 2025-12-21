# scripts/test_uncertainty_service.py
from __future__ import annotations

from src.models.uncertainty_service import UncertaintyService


def main():
    svc = UncertaintyService()

    profile = {
        "governorate": "Tunis",
        "activity_type": "grocery",
        "density_per_km2": 5000,
        "poi_per_km2": 120,
        "years_active": 5,
        "shop_area_m2": 40,
        "assets_value_tnd": 60000,
        "revenue_monthly_tnd": 8000,
        "open_at_night": 0,
        "security_alarm": 1,
        "security_camera": 1,
        "fire_extinguisher": 1,
    }

    res = svc.predict(profile)
    print("uncertainty_score:", res.uncertainty_score)
    print("uncertainty_band:", res.uncertainty_band)


if __name__ == "__main__":
    main()
