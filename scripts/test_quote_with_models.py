# scripts/test_quote_with_models.py
from __future__ import annotations

from src.api.schemas import QuoteRequest, SecurityFeatures
from src.pricing.service import compute_quote


def main():
    req = QuoteRequest(
        governorate="Tunis",
        activity_type="grocery",
        shop_area_m2=40,
        years_active=5,
        assets_value_tnd=60000,
        revenue_monthly_tnd=8000,
        open_at_night=False,
        security=SecurityFeatures(has_alarm=True, has_camera=True, has_extinguisher=True),
        budget_constraint_tnd=300,
    )

    resp = compute_quote(req)
    bd = resp.offer.breakdown

    print("=== Quote breakdown keys ===")
    print(sorted(list(bd.keys())))

    print("\n=== Key model outputs ===")
    print("p_claim:", bd.get("p_claim"))
    print("expected_cost:", bd.get("expected_cost"))
    print("uncertainty_score:", bd.get("uncertainty_score"))
    print("uncertainty_band:", bd.get("uncertainty_band"))

    print("\n=== Offer ===")
    print("template:", resp.offer.template_id, resp.offer.template_name)
    print("premium:", resp.offer.prime_annuelle_tnd)
    print("plafond:", resp.offer.plafond_tnd)
    print("franchise:", resp.offer.franchise_tnd)

    print("\n=== Budget / Floor checks ===")
    print("budget_target:", bd.get("budget_target"))
    print("budget_applied:", bd.get("budget_applied"))
    print("budget_unmet:", bd.get("budget_unmet"))
    print("min_premium_applied:", bd.get("min_premium_applied"))
    print("min_premium_value:", bd.get("min_premium_value"))
    print("premium_raw:", bd.get("premium_raw"))



if __name__ == "__main__":
    main()
