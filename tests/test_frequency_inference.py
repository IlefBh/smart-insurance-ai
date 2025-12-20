from src.models.frequency_service import FrequencyService


def test_bool_strings_are_not_truthy():
    svc = FrequencyService()

    p = svc.predict({
        "density_per_km2": 5000,
        "poi_per_km2": 200,
        "years_active": 8,
        "shop_area_m2": 60,
        "assets_value_tnd": 20000,
        "revenue_monthly_tnd": 5000,
        "governorate": "Tunis",
        "activity_type": "grocery",
        "open_at_night": "False",         # string
        "security_alarm": "0",            # string
        "security_camera": "False",       # string
        "fire_extinguisher": "no",         # string
    })

    assert 0.0 <= p <= 1.0
    assert p < 0.30
