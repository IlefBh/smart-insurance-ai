# tests/test_uncertainty_deeponet_integration.py
from __future__ import annotations

from src.api.schemas import QuoteRequest, SecurityFeatures
from src.pricing.service import compute_quote  # <-- adapte si ton module n'est pas src.pricing.service


def test_deeponet_uncertainty_is_in_response_breakdown():
    req = QuoteRequest(
        governorate="Tunis",
        activity_type="grocery",
        shop_area_m2=40,
        years_active=0,
        assets_value_tnd=60000,
        revenue_monthly_tnd=8000,
        open_at_night=True,
        security=SecurityFeatures(has_alarm=False, has_camera=False, has_extinguisher=True),
        budget_constraint_tnd=1200,
    )

    resp = compute_quote(req)
    bd = resp.offer.breakdown
    assert "uncertainty_score" in bd
    assert "uncertainty_buffer" in bd

    score = float(bd["uncertainty_score"])
    assert 0.0 <= score <= 1.0

    # band est maintenant dans explain
    assert resp.offer.explain["uncertainty_band"] in {"LOW", "MEDIUM", "HIGH"}


def test_uncertainty_changes_when_profile_changes():
    # Profil A
    req_a = QuoteRequest(
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
    # Profil B (changement clair)
    req_b = QuoteRequest(
        governorate="Tunis",
        activity_type="grocery",
        shop_area_m2=40,
        years_active=0,
        assets_value_tnd=60000,
        revenue_monthly_tnd=8000,
        open_at_night=True,
        security=SecurityFeatures(has_alarm=False, has_camera=False, has_extinguisher=True),
        budget_constraint_tnd=1200,
    )

    resp_a = compute_quote(req_a)
    resp_b = compute_quote(req_b)

    score_a = float(resp_a.offer.breakdown["uncertainty_score"])
    score_b = float(resp_b.offer.breakdown["uncertainty_score"])

    # Scores valides
    assert 0.0 <= score_a <= 1.0
    assert 0.0 <= score_b <= 1.0

    # Le modèle doit réagir (non constant)
    assert abs(score_a - score_b) >= 1e-6

    # Le buffer doit être cohérent avec le score (même sens) si ton engine le calcule par seuils
    buf_a = float(resp_a.offer.breakdown["uncertainty_buffer"])
    buf_b = float(resp_b.offer.breakdown["uncertainty_buffer"])

    if score_b > score_a:
        assert buf_b >= buf_a
    elif score_b < score_a:
        assert buf_b <= buf_a
