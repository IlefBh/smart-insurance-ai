# src/pricing/rules.py
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .templates import ProductTemplate, TEMPLATES


@dataclass
class SelectionDecision:
    template_id: str
    reasons: List[str]
    candidates: List[str]


def _eligible(t: ProductTemplate, profile: Dict) -> bool:
    # activity check
    if t.activity_in is not None:
        if profile.get("activity_type") not in t.activity_in:
            return False

    # night check
    if t.open_at_night_required is not None:
        if bool(profile.get("open_at_night")) != bool(t.open_at_night_required):
            return False

    assets = float(profile.get("assets_value_tnd", 0) or 0)

    if t.assets_min_tnd is not None and assets < t.assets_min_tnd:
        return False
    if t.assets_max_tnd is not None and assets > t.assets_max_tnd:
        return False

    return True


def select_template(profile: Dict, risk: Dict) -> SelectionDecision:
    """
    Deterministic selection:
    - Build eligible candidates
    - Score them using risk signals (p_claim, uncertainty) and profile patterns
    - Return chosen template + reason codes
    """
    candidates = [tid for tid, t in TEMPLATES.items() if _eligible(t, profile)]
    reasons: List[str] = []

    # fallback if none (shouldn't happen in MVP)
    if not candidates:
        return SelectionDecision(template_id="T1_ESSENTIEL", reasons=["fallback_default"], candidates=["T1_ESSENTIEL"])

    p_claim = float(risk.get("p_claim", 0.0) or 0.0)
    unc = risk.get("uncertainty_score", 0.0)
    open_at_night = bool(profile.get("open_at_night"))

    # scoring: higher score means better fit
    scores: Dict[str, float] = {tid: 0.0 for tid in candidates}

    for tid in candidates:
        t = TEMPLATES[tid]
        # base preference logic
        if tid == "T3_NIGHT" and open_at_night:
            scores[tid] += 2.0
        if tid == "T2_PLUS" and profile.get("activity_type") in ["pharmacy", "electronics"]:
            scores[tid] += 1.5
        if tid == "T1_ESSENTIEL":
            scores[tid] += 1.0

        # risk-aware nudges
        if p_claim > 0.15 and tid == "T3_NIGHT":
            scores[tid] += 1.0
        if unc and unc > 0.6:
            # if uncertainty high, prefer templates with stricter underwriting (often night/cash)
            if tid in ["T3_NIGHT", "T2_PLUS"]:
                scores[tid] += 0.5

    chosen = max(scores.items(), key=lambda x: x[1])[0]

    # reason codes for explainability
    if chosen == "T3_NIGHT":
        reasons.append("rule_open_at_night")
        if p_claim > 0.15:
            reasons.append("rule_high_frequency")
    elif chosen == "T2_PLUS":
        reasons.append("rule_activity_high_value")
    else:
        reasons.append("rule_default_essential")

    return SelectionDecision(template_id=chosen, reasons=reasons, candidates=candidates)
