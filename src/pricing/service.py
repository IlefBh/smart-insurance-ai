from __future__ import annotations

from typing import Dict, Any

from src.api.schemas import (
    QuoteRequest,
    QuoteResponse,
    SelectionDecision as ApiDecision,
    Offer as ApiOffer,
)
from src.pricing.rules import select_template
from src.pricing.engine import build_offer


def _normalize_profile(req: QuoteRequest) -> Dict[str, Any]:
    """
    API schema -> pricing schema expected by rules/engine.
    This is the only translation layer, so schema changes remain localized.
    """
    r = req.model_dump()
    sec = r.get("security") or {}

    profile: Dict[str, Any] = {
        "governorate": r.get("governorate"),
        "activity_type": r.get("activity_type"),
        "shop_area_m2": r.get("shop_area_m2"),
        "years_active": r.get("years_active"),
        "assets_value_tnd": r.get("assets_value_tnd"),
        "revenue_bucket": r.get("revenue_bucket"),
        "open_at_night": bool(r.get("open_at_night", False)),

        # expected by pricing/engine.py
        "security_alarm": bool(sec.get("has_alarm", False)),
        "security_camera": bool(sec.get("has_camera", False)),
        "fire_extinguisher": bool(sec.get("has_extinguisher", False)),

        # keep for future rules (not used in engine currently)
        "security_guard": bool(sec.get("has_guard", False)),

        # engine expects budget_max_tnd (spec). API currently uses budget_constraint_tnd.
        "budget_max_tnd": r.get("budget_constraint_tnd"),
    }

    return profile


def _stub_risk_estimates(profile: Dict[str, Any]) -> Dict[str, float]:
    """
    Deterministic, explainable risk proxies until models are plugged in.
    Keys expected by rules/engine:
      - p_claim
      - expected_cost
      - uncertainty_score
    """
    assets = float(profile.get("assets_value_tnd") or 0.0)
    open_at_night = bool(profile.get("open_at_night"))
    alarm = bool(profile.get("security_alarm"))
    camera = bool(profile.get("security_camera"))
    years_active = int(profile.get("years_active") or 0)

    # Frequency proxy
    p_claim = 0.06
    if open_at_night:
        p_claim += 0.08
    if assets > 60000:
        p_claim += 0.05
    if not alarm:
        p_claim += 0.04
    if camera:
        p_claim -= 0.01
    p_claim = max(0.0, min(0.60, p_claim))

    # Severity proxy (TND)
    if assets > 80000:
        expected_cost = 9000.0
    elif assets > 30000:
        expected_cost = 6000.0
    else:
        expected_cost = 4500.0

    # Uncertainty proxy
    uncertainty_score = 0.30
    if years_active < 1:
        uncertainty_score += 0.15
    if profile.get("revenue_bucket") == "low":
        uncertainty_score += 0.05
    if open_at_night and not alarm:
        uncertainty_score += 0.20
    uncertainty_score = max(0.0, min(1.0, uncertainty_score))

    return {
        "p_claim": float(p_claim),
        "expected_cost": float(expected_cost),
        "uncertainty_score": float(uncertainty_score),
    }


def compute_quote(req: QuoteRequest) -> QuoteResponse:
    profile = _normalize_profile(req)

    # Later: replace by models outputs
    risk = _stub_risk_estimates(profile)

    decision = select_template(profile, risk)
    risk["template_id"] = decision.template_id  # engine expects template_id in risk dict

    priced_offer = build_offer(profile, risk, decision.reasons)

    api_decision = ApiDecision(
        template_id=decision.template_id,
        candidates=decision.candidates,
        reasons=decision.reasons,
    )

    api_offer = ApiOffer(
        template_id=priced_offer.template_id,
        template_name=priced_offer.template_name,
        coverages=priced_offer.coverages,
        plafond_tnd=priced_offer.plafond_tnd,
        franchise_tnd=priced_offer.franchise_tnd,
        prime_annuelle_tnd=priced_offer.prime_annuelle_tnd,
        breakdown=priced_offer.breakdown,
    )

    return QuoteResponse(decision=api_decision, offer=api_offer)
