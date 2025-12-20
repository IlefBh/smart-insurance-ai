# src/pricing/service.py
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
from src.models.segmentation_runtime import predict_cluster_id, cluster_to_template_hint

# ✅ Keep DeepONet uncertainty only (no frequency duplication)
from src.models.uncertainty_service import UncertaintyService


def revenue_to_bucket(revenue_monthly_tnd: float) -> str:
    """
    Deterministic bucketing (proxy). Adjust thresholds if needed.
    """
    try:
        r = float(revenue_monthly_tnd or 0.0)
    except Exception:
        r = 0.0

    if r < 3000:
        return "low"
    if r < 8000:
        return "medium"
    return "high"


def _request_to_dict(req: QuoteRequest) -> Dict[str, Any]:
    if hasattr(req, "model_dump"):
        return req.model_dump()
    if hasattr(req, "dict"):
        return req.dict()
    return dict(req)  # type: ignore


def compute_quote(req: QuoteRequest) -> QuoteResponse:
    payload = _request_to_dict(req)

    # Build profile (X) — keep your dataset schema
    profile: Dict[str, Any] = {
        "IDpol": payload.get("IDpol"),
        "governorate": payload.get("governorate"),
        "density_per_km2": payload.get("density_per_km2"),
        "poi_per_km2": payload.get("poi_per_km2"),
        "years_active": payload.get("years_active"),
        "activity_type": payload.get("activity_type"),
        "shop_area_m2": payload.get("shop_area_m2"),
        "assets_value_tnd": payload.get("assets_value_tnd"),
        "revenue_monthly_tnd": payload.get("revenue_monthly_tnd"),
        "revenue_bucket": payload.get("revenue_bucket"),
        "open_at_night": payload.get("open_at_night", False),
        "security_alarm": payload.get("security_alarm", False),
        "security_camera": payload.get("security_camera", False),
        "fire_extinguisher": payload.get("fire_extinguisher", False),
        "budget_constraint_tnd": payload.get("budget_constraint_tnd"),
    }

    # If revenue_bucket missing, infer deterministically
    if not profile.get("revenue_bucket"):
        profile["revenue_bucket"] = revenue_to_bucket(float(profile.get("revenue_monthly_tnd") or 0.0))

    # ======================
    # Risk inputs (Models)
    # ======================
    # Model2 (frequency) & Model3 (severity): use values if provided by upstream pipeline,
    # otherwise keep placeholders (temporary).
    risk: Dict[str, Any] = {
        "p_claim": payload.get("p_claim", 0.10),                # placeholder if not computed yet
        "expected_cost": payload.get("expected_cost", 3000.0),  # placeholder if not computed yet
    }

    # Model4 (DeepONet) — uncertainty only (never sets prices)
    unc = UncertaintyService().predict(profile)
    risk["uncertainty_score"] = float(unc.uncertainty_score)
    risk["uncertainty_band"] = getattr(unc, "uncertainty_band", None)

    # ======================
    # Segmentation (Model 1)
    # ======================
    cluster_id = predict_cluster_id(profile)
    risk["cluster_id"] = cluster_id

    hint_tid = cluster_to_template_hint(cluster_id)
    if hint_tid:
        risk["cluster_hint_template_id"] = hint_tid

    # ======================
    # Product selection (rules)
    # ======================
    decision = select_template(profile, risk)

    # ======================
    # Pricing (deterministic)
    # ======================
    # IMPORTANT: keep your engine signature (profile, risk, decision)
    priced_offer = build_offer(profile, risk, decision)

    # ======================
    # API response
    # ======================
    reasons_extra = [
        f"derived_revenue_bucket:{profile['revenue_bucket']}",
        f"segmentation_cluster_id:{cluster_id}",
        f"cluster_hint:{hint_tid}" if hint_tid else "cluster_hint:none",
        "uncertainty_model:deeponet_v1",
        f"uncertainty_band:{risk.get('uncertainty_band')}",
    ]

    api_decision = ApiDecision(
        template_id=decision.template_id,
        reasons=decision.reasons + reasons_extra,
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
            "uncertainty_band": risk.get("uncertainty_band"),
            "uncertainty_score": risk.get("uncertainty_score"),
        },
    )

    return QuoteResponse(decision=api_decision, offer=api_offer)