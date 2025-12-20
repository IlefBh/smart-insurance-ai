# src/features/schemas.py

# =========================
# Segmentation (Model 1)
# =========================

SEGMENTATION_FEATURES = [
    "governorate",
    "density_per_km2",
    "poi_per_km2",
    "years_active",
    "activity_type",
    "shop_area_m2",
    "assets_value_tnd",
    "revenue_monthly_tnd",
    "revenue_bucket",
    "open_at_night",
    "security_alarm",
    "security_camera",
    "fire_extinguisher",
]

SEGMENTATION_CAT_COLS = [
    "governorate",
    "activity_type",
    "revenue_bucket",
]

SEGMENTATION_BOOL_COLS = [
    "open_at_night",
    "security_alarm",
    "security_camera",
    "fire_extinguisher",
]

SEGMENTATION_NUM_COLS = [
    "density_per_km2",
    "poi_per_km2",
    "years_active",
    "shop_area_m2",
    "assets_value_tnd",
    "revenue_monthly_tnd",
]

# Labels (excluded from segmentation)
LABEL_COLS = [
    "claim_occurred",
    "claim_cost_tnd",
]

# Product names (must match what you show in UI / templates)
PRODUCT_ESSENTIEL = "Commerce Essentiel"
PRODUCT_PLUS = "Commerce Plus"
PRODUCT_NIGHT = "Night & Cash Risk"
