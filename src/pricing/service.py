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

from src.models.uncertainty_service import UncertaintyService
from src.models.frequency_service import FrequencyService
from src.models.geo_proxies import GeoProxies



SECURITY_MAP = {
    "has_alarm": "security_alarm",
    "has_camera": "security_camera",
    "has_extinguisher": "fire_extinguisher",
}

def _normalize_profile(req: QuoteRequest) -> Dict[str, Any]:
    r = req.model_dump()

    sec = r.get("security") or {}
    gov = r.get("governorate")
    density, poi = GeoProxies().get(str(gov))

    profile: Dict[str, Any] = {
        "governorate": (r.get("governorate") or "").strip(),
        "activity_type": (r.get("activity_type") or "").strip(),
        "shop_area_m2": r.get("shop_area_m2"),
        "years_active": r.get("years_active"),
        "assets_value_tnd": r.get("assets_value_tnd"),
        "revenue_monthly_tnd": r.get("revenue_monthly_tnd"),
        "open_at_night": r.get("open_at_night"),
        "density_per_km2": density,
        "poi_per_km2": poi,
    }

    # IMPORTANT: map API security keys to training feature names
    for api_key, feat_key in SECURITY_MAP.items():
        profile[feat_key] = sec.get(api_key)

    return profile

def _stub_risk_estimates(profile: Dict[str, Any]) -> Dict[str, float]:
    """
    Deterministic, explainable risk proxies until models are plugged in.
    Keys expected by rules/engine:
      - p_claim
      - expected_cost
    NOTE: uncertainty_score is provided by DeepONet (model 4), not a stub.
    """
    assets = float(profile.get("assets_value_tnd") or 0.0)
    open_at_night = bool(profile.get("open_at_night"))
    alarm = bool(profile.get("security_alarm"))
    camera = bool(profile.get("security_camera"))

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

    return {
        "p_claim": float(p_claim),
        "expected_cost": float(expected_cost),
    }


def compute_quote(req: QuoteRequest) -> QuoteResponse:
    profile = _normalize_profile(req)

    # Proxies for now (models 2 & 3 later)
    risk = _stub_risk_estimates(profile)
    # Model 2 (Frequency) - calibrated, never pricing
    try:
        p_claim_ml = FrequencyService().predict(profile)
        risk["p_claim"] = float(p_claim_ml)
        freq_reason = "frequency_model:logreg_calibrated_v1"
    except FileNotFoundError:
        # fallback safe
        freq_reason = "frequency_model:fallback_stub"


    # Model 4 (DeepONet) - uncertainty only, never pricing
    unc = UncertaintyService().predict(profile)
    risk["uncertainty_score"] = float(unc.uncertainty_score)
    # audit trace
    risk["uncertainty_band"] = unc.uncertainty_band

    # Rule-based selection (deterministic)
    decision = select_template(profile, risk)
    risk["template_id"] = decision.template_id  # engine expects template_id in risk dict

    # Actuarial pricing engine (deterministic)
    priced_offer = build_offer(profile, risk, decision.reasons)

    # Add explanation codes (audit-friendly)
    extra_reasons = [
         freq_reason,
        "uncertainty_model:deeponet_v1",
        f"uncertainty_band:{unc.uncertainty_band}",
    ]

    # Optionally enrich breakdown for traceability
    # (safe even if UI ignores it)
    try:
        priced_offer.breakdown["uncertainty_score"] = float(unc.uncertainty_score)
    except Exception:
        # if breakdown is immutable in your Offer implementation, ignore
        pass

    api_decision = ApiDecision(
        template_id=decision.template_id,
        candidates=decision.candidates,
        reasons=decision.reasons + extra_reasons,
    )

    api_offer = ApiOffer(
        template_id=priced_offer.template_id,
        template_name=priced_offer.template_name,
        coverages=priced_offer.coverages,
        plafond_tnd=priced_offer.plafond_tnd,
        franchise_tnd=priced_offer.franchise_tnd,
        prime_annuelle_tnd=priced_offer.prime_annuelle_tnd,
        breakdown=priced_offer.breakdown,
        explain={
            "uncertainty_model": "deeponet_v1",
            "uncertainty_band": unc.uncertainty_band,
        },
    )

    return QuoteResponse(decision=api_decision, offer=api_offer)
