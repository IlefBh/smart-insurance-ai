from pprint import pprint

from src.pricing.rules import select_template
from src.pricing.engine import build_offer

# 1) Fake profile (like UI form)
profile = {
    "governorate": "Sfax",
    "activity_type": "grocery",
    "shop_area_m2": 60,
    "assets_value_tnd": 40000,
    "revenue_bucket": "medium",
    "open_at_night": True,
    "security_alarm": False,
    "security_camera": True,
    "fire_extinguisher": True,
    "budget_max_tnd": 900,
}

# 2) Stub risk outputs (later replaced by ML)
risk = {"p_claim": 0.18, "expected_cost": 2500, "uncertainty_score": 0.65}

# 3) Template selection (rules)
decision = select_template(profile, risk)
risk["template_id"] = decision.template_id

# 4) Pricing (actuarial engine)
offer = build_offer(profile, risk, decision.reasons)

print("\n=== Decision ===")
pprint(decision)

print("\n=== Offer ===")
pprint(offer)
