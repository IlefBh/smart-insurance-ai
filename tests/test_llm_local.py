"""
E2E local test for LLM explanation layer.
- Runs the real pricing pipeline (compute_quote)
- Feeds the real output to OfferExplainer
- Works in fallback mode (no API key required)
"""

from __future__ import annotations

import os

from src.api.schemas import QuoteRequest, SecurityFeatures
from src.pricing.service import compute_quote
from src.llm.explainer import OfferExplainer


def _build_client_profile_from_req(req: QuoteRequest) -> dict:
    """
    Build the client_profile dict expected by prompts.py.
    We keep it simple and explicit to avoid hidden dependencies (_normalize_profile).
    """
    payload = req.model_dump() if hasattr(req, "model_dump") else dict(req)

    # Extract nested security
    sec = payload.get("security") or {}
    # SecurityFeatures likely uses has_alarm/has_camera/has_extinguisher
    security_alarm = bool(sec.get("has_alarm", False))
    security_camera = bool(sec.get("has_camera", False))
    fire_extinguisher = bool(sec.get("has_extinguisher", False))

    # Ensure keys used in prompts are present
    payload["security_alarm"] = security_alarm
    payload["security_camera"] = security_camera
    payload["fire_extinguisher"] = fire_extinguisher

    return payload


def main():
    # Same request as your models test
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

    # Convert offer to dict
    offer_dict = resp.offer.model_dump() if hasattr(resp.offer, "model_dump") else dict(resp.offer)

    # Attach decision reasons under the key expected by your explainer/prompts
    decision_dict = resp.decision.model_dump() if hasattr(resp.decision, "model_dump") else dict(resp.decision)
    offer_dict["decision_reasons"] = decision_dict.get("reasons", [])

    # Ensure flags exist (even if empty)
    if "flags" not in offer_dict:
        offer_dict["flags"] = {}

    # Client profile (what the prompt expects)
    client_profile = _build_client_profile_from_req(req)

    # ML outputs (keep minimal, no invention)
    breakdown = offer_dict.get("breakdown", {}) or {}
    ml_outputs = {
        "segment_name": "N/A",
        "uncertainty_score": breakdown.get("uncertainty_score", None),
    }

    api_key = os.getenv("GOOGLE_API_KEY")

    # If key exists, use real API; otherwise fallback.
    explainer = OfferExplainer(api_key=api_key)

    out = explainer.generate_explanations(
        offer=offer_dict,
        client_profile=client_profile,
        ml_outputs=ml_outputs,
    )

    print("\n" + "=" * 70)
    print("✅ LLM EXPLAINER E2E TEST")
    print("=" * 70)
    print("\n📋 CUSTOMER EXPLANATION:")
    print("-" * 70)
    print(out.customer_explanation)

    print("\n🔍 INSURER EXPLANATION:")
    print("-" * 70)
    print(out.insurer_explanation)

    print("\n💡 RECOMMENDATIONS:")
    print("-" * 70)
    print(out.recommendations)

    print("\n⚠️ DISCLAIMER:")
    print("-" * 70)
    print(out.disclaimer)

    print("\n" + "=" * 70)
    print("✅ TEST COMPLETED")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
