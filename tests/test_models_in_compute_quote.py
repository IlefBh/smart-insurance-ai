from src.api.schemas import QuoteRequest, SecurityFeatures
from src.pricing.service import compute_quote


def test_compute_quote_uses_frequency_model_calibrated():
    req = QuoteRequest(
        governorate="Tunis",
        activity_type="grocery",
        shop_area_m2=40,
        years_active=8,
        assets_value_tnd=60000,
        revenue_monthly_tnd=8000,
        open_at_night=False,
        security=SecurityFeatures(has_alarm=True, has_camera=True, has_extinguisher=True),
        budget_constraint_tnd=1200,
    )

    resp = compute_quote(req)
    bd = resp.offer.breakdown

    assert "p_claim" in bd
    p = float(bd["p_claim"])
    assert 0.0 <= p <= 1.0

    # Calibrated model on 96/4 should usually give small probabilities for stable profiles
    assert p < 0.20

    # Audit reason should mention calibrated model (if artifacts exist)
    assert any("frequency_model:logreg_calibrated_v1" in r for r in resp.decision.reasons)
