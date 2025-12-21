# src/pricing/service.py
from __future__ import annotations

from typing import Dict, Any, Tuple
from pathlib import Path

import pandas as pd

from src.api.schemas import (
    QuoteRequest,
    QuoteResponse,
    SelectionDecision as ApiDecision,
    Offer as ApiOffer,
)

from src.pricing.rules import select_template
from src.pricing.engine import build_offer

from src.models.segmentation_runtime import predict_cluster_id, cluster_to_template_hint

from src.models.frequency import load_frequency_model, predict_p_claim
from src.models.severity import load_severity_model

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


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _sanitize_risk_outputs(p_claim: float, expected_cost: float) -> Tuple[float, float]:
    """
    Hackathon safety:
    - In your artifact audit, p_claim max ~0.243 -> cap at 0.25
    - expected_cost should not be absurdly low/high
    """
    p = float(p_claim)
    c = float(expected_cost)

    # never 0, never insane high (keeps pricing stable)
    p = _clamp(p, 0.001, 0.25)

    # keep severity reasonable (TND)
    c = _clamp(c, 500.0, 50000.0)

    return p, c


# simple cache in module scope (avoid reloading artifacts each request)
_FREQ_MODEL = None
_SEV_MODEL = None


def _get_freq_model():
    global _FREQ_MODEL
    if _FREQ_MODEL is None:
        _FREQ_MODEL = load_frequency_model()
    return _FREQ_MODEL


def _get_sev_model():
    global _SEV_MODEL
    if _SEV_MODEL is None:
        _SEV_MODEL = load_severity_model()
    return _SEV_MODEL


def compute_quote(req: QuoteRequest) -> QuoteResponse:
    payload = _request_to_dict(req)

    # Build profile (X) — match training schema
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

    # Prepare dataframe for sklearn models (must include all SEGMENTATION_FEATURES columns)
    X = pd.DataFrame(
        [
            {
                "governorate": profile.get("governorate"),
                "density_per_km2": profile.get("density_per_km2"),
                "poi_per_km2": profile.get("poi_per_km2"),
                "years_active": profile.get("years_active"),
                "activity_type": profile.get("activity_type"),
                "shop_area_m2": profile.get("shop_area_m2"),
                "assets_value_tnd": profile.get("assets_value_tnd"),
                "revenue_monthly_tnd": profile.get("revenue_monthly_tnd"),
                "revenue_bucket": profile.get("revenue_bucket"),
                "open_at_night": int(bool(profile.get("open_at_night", False))),
                "security_alarm": int(bool(profile.get("security_alarm", False))),
                "security_camera": int(bool(profile.get("security_camera", False))),
                "fire_extinguisher": int(bool(profile.get("fire_extinguisher", False))),
            }
        ]
    )

    # ======================
    # Risk inputs (Models)
    # ======================
    # Frequency (Model 2)
    freq_model = _get_freq_model()
    p_claim = predict_p_claim(freq_model, X)

    # Severity (Model 3) - conditional expected cost given a claim
    sev_model = _get_sev_model()
    expected_cost = float(sev_model.predict(X)[0])

    # sanitize (critical for stability)
    p_claim, expected_cost = _sanitize_risk_outputs(p_claim, expected_cost)

    risk: Dict[str, Any] = {
        "p_claim": p_claim,
        "expected_cost": expected_cost,
    }

    # ======================
    # Uncertainty (Model 4 DeepONet) — score only (non-blocking)
    # ======================
    uncertainty_fallback_used = 0.0
    try:
        unc = UncertaintyService().predict(profile)
        risk["uncertainty_score"] = float(unc.uncertainty_score)
    except Exception:
        risk["uncertainty_score"] = 0.50
        uncertainty_fallback_used = 1.0

    # If artifacts are missing, flag fallback (audit-friendly)
    try:
        if not Path("artifacts/uncertainty_deeponet/meta.json").exists():
            uncertainty_fallback_used = 1.0
    except Exception:
        uncertainty_fallback_used = 1.0

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
    priced_offer = build_offer(profile, risk, decision)

    # Ensure breakdown stays numeric-only (pydantic expects Dict[str, float])
    breakdown = dict(priced_offer.breakdown)
    breakdown["uncertainty_score"] = float(risk.get("uncertainty_score", 0.0))
    breakdown["uncertainty_fallback_used"] = float(uncertainty_fallback_used)

    # ======================
    # API response
    # ======================
    reasons_extra = [
        f"derived_revenue_bucket:{profile['revenue_bucket']}",
        f"segmentation_cluster_id:{cluster_id}",
        f"cluster_hint:{hint_tid}" if hint_tid else "cluster_hint:none",
        "uncertainty_model:deeponet_v1",
        f"uncertainty_score:{risk.get('uncertainty_score')}",
        f"uncertainty_fallback_used:{bool(uncertainty_fallback_used)}",
        "frequency_model:sklearn_logreg_v1",
        "severity_model:sklearn_gamma_v1",
        "risk_outputs_sanitized:true",
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
        breakdown=breakdown,
        explain={
            "uncertainty_model": "deeponet_v1",
            "uncertainty_score": risk.get("uncertainty_score"),
            "uncertainty_fallback_used": bool(uncertainty_fallback_used),
            "frequency_model": "sklearn_logreg_v1",
            "severity_model": "sklearn_gamma_v1",
        },
    )

    return QuoteResponse(decision=api_decision, offer=api_offer)
