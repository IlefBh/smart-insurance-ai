# src/pricing/rules.py
from dataclasses import dataclass
from typing import Dict, List

from .templates import ProductTemplate, TEMPLATES


@dataclass
class SelectionDecision:
    template_id: str
    reasons: List[str]
    candidates: List[str]


def _eligible(t: ProductTemplate, profile: Dict) -> bool:
    activity = (profile.get("activity_type") or "").lower()
    open_at_night = bool(profile.get("open_at_night", False))
    assets = float(profile.get("assets_value_tnd", 0.0) or 0.0)

    if t.activity_in is not None:
        allowed = [a.lower() for a in t.activity_in]
        if activity not in allowed:
            return False

    if t.open_at_night_required is not None:
        if open_at_night != bool(t.open_at_night_required):
            return False

    if t.assets_min_tnd is not None and assets < float(t.assets_min_tnd):
        return False

    if t.assets_max_tnd is not None and assets > float(t.assets_max_tnd):
        return False

    return True


def select_template(profile: Dict, risk: Dict) -> SelectionDecision:
    """
    Deterministic selection.
    Uses: open_at_night, activity/assets exposure, ML outputs (p_claim, uncertainty)
    plus optional segmentation hint:
        risk["cluster_hint_template_id"] in {"T1_ESS","T2_PLUS","T3_NIGHT"}
    """
    reasons: List[str] = []
    candidates: List[str] = []

    for tid, t in TEMPLATES.items():
        if _eligible(t, profile):
            candidates.append(tid)

    if not candidates:
        # Should never happen, but keep safe fallback
        return SelectionDecision(template_id="T1_ESS", reasons=["fallback_no_candidate"], candidates=[])

    # Base scoring
    scores = {tid: 0.0 for tid in candidates}

    open_at_night = bool(profile.get("open_at_night", False))
    assets = float(profile.get("assets_value_tnd", 0.0) or 0.0)
    activity = (profile.get("activity_type") or "").lower()

    p_claim = float(risk.get("p_claim", 0.0) or 0.0)
    uncertainty = float(risk.get("uncertainty_score", 0.0) or 0.0)

    # 1) Segmentation hint (orientation only)
    hint = risk.get("cluster_hint_template_id")
    if hint in scores:
        scores[hint] += 1.5
        reasons.append(f"rule_cluster_profile_hint:{hint}")

    # 2) Night rule
    if open_at_night and "T3_NIGHT" in scores:
        scores["T3_NIGHT"] += 2.0
        reasons.append("rule_open_at_night")

    # 3) High exposure rule (assets/activity)
    high_value_activity = any(k in activity for k in ["pharm", "electron", "bijou", "jewel"])
    if (assets >= 80000 or high_value_activity) and "T2_PLUS" in scores:
        scores["T2_PLUS"] += 1.5
        reasons.append("rule_high_exposure_assets_or_activity")

    # 4) Frequency / uncertainty nudges (still deterministic)
    if p_claim > 0.15:
        # prefer more protective templates if eligible
        if "T2_PLUS" in scores:
            scores["T2_PLUS"] += 0.4
        if "T3_NIGHT" in scores:
            scores["T3_NIGHT"] += 0.4
        reasons.append("rule_high_frequency")

    if uncertainty > 0.7:
        # uncertainty -> prefer simpler base product unless night required
        if "T1_ESS" in scores:
            scores["T1_ESS"] += 0.3
        reasons.append("rule_high_uncertainty")

    chosen = max(scores.items(), key=lambda x: x[1])[0]

    # Add final summary reason for chosen
    if chosen == "T3_NIGHT":
        reasons.append("chosen_night_template")
    elif chosen == "T2_PLUS":
        reasons.append("chosen_plus_template")
    else:
        reasons.append("chosen_essential_template")

    return SelectionDecision(template_id=chosen, reasons=reasons, candidates=candidates)
