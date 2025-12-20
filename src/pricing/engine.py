# src/pricing/engine.py
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from .templates import ProductTemplate, TEMPLATES


@dataclass
class Offer:
    template_id: str
    template_name: str
    coverages: List[str]

    plafond_tnd: float
    franchise_tnd: float
    prime_annuelle_tnd: float

    bbreakdown: Dict[str, float]
    decision_reasons: List[str]
    flags: Dict[str, bool]


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def compute_plafond(profile: Dict, t: ProductTemplate) -> float:
    assets = float(profile.get("assets_value_tnd", 0) or 0)
    # simple: cover up to 90% of assets, constrained by template bounds
    raw = 0.9 * assets if assets > 0 else t.plafond_base_tnd
    return _clip(raw, t.plafond_min_tnd, t.plafond_max_tnd)


def compute_franchise(profile: Dict, t: ProductTemplate, risk: Dict) -> float:
    base = t.franchise_base_tnd
    open_at_night = bool(profile.get("open_at_night"))
    alarm = bool(profile.get("security_alarm"))
    unc = float(risk.get("uncertainty_score", 0.0) or 0.0)
    p_claim = float(risk.get("p_claim", 0.0) or 0.0)

    # Adjustments (simple, explainable)
    if open_at_night:
        base += 300
    if not alarm:
        base += 200
    if p_claim > 0.2:
        base += 300
    if unc > 0.6:
        base += 400

    return _clip(base, t.franchise_min_tnd, t.franchise_max_tnd)


def compute_premium(profile: Dict, t: ProductTemplate, risk: Dict, franchise: float) -> Dict:
    """
    Premium = expected_loss * (1 + base_expense_margin + uncertainty_buffer)
    + small discounts/penalties based on safety features.
    """
    p_claim = float(risk.get("p_claim", 0.0) or 0.0)
    sev = float(risk.get("expected_cost", 0.0) or 0.0)
    unc = float(risk.get("uncertainty_score", 0.0) or 0.0)

    expected_loss = p_claim * sev

    # uncertainty buffer (simple)
    if unc > 0.75:
        unc_buf = 0.20
    elif unc > 0.60:
        unc_buf = 0.15
    elif unc > 0.40:
        unc_buf = 0.08
    else:
        unc_buf = 0.03

    multiplier = 1.0 + t.base_expense_margin + unc_buf

    # safety discounts / maluses
    camera = bool(profile.get("security_camera"))
    alarm = bool(profile.get("security_alarm"))
    extinguisher = bool(profile.get("fire_extinguisher"))

    adj = 1.0
    if camera:
        adj *= 0.95
    if alarm:
        adj *= 0.93
    else:
        adj *= 1.07
    if extinguisher:
        adj *= 0.97

    premium = expected_loss * multiplier * adj

    # optional: reflect higher deductible => slightly lower premium
    # (risk sharing)
    premium *= (1.0 - min(0.10, (franchise / 10000.0)))

    # budget cap (if provided)
    budget = profile.get("budget_max_tnd")
    if budget is not None:
        try:
            budget = float(budget)
            if budget > 0:
                premium = min(premium, budget)
        except Exception:
            pass

    breakdown = {
        "p_claim": p_claim,
        "expected_cost": sev,
        "expected_loss": expected_loss,
        "expense_margin": t.base_expense_margin,
        "uncertainty_buffer": unc_buf,
        "multiplier": multiplier,
        "feature_adjustment": adj,
    }

    return {"premium": float(max(0.0, premium)), "breakdown": breakdown}


def build_offer(profile: Dict, risk: Dict, decision_reasons: List[str]) -> Offer:
    template_id = risk.get("template_id")
    if not template_id:
        template_id = "T1_ESSENTIEL"
    t = TEMPLATES[template_id]

    plafond = compute_plafond(profile, t)
    franchise = compute_franchise(profile, t, risk)
    prem = compute_premium(profile, t, risk, franchise)

    flags = {
        "underwriting_review": bool(float(risk.get("uncertainty_score", 0.0) or 0.0) > 0.7),
        "high_risk": bool(float(risk.get("p_claim", 0.0) or 0.0) > 0.25),
    }

    return Offer(
        template_id=t.id,
        template_name=t.name,
        coverages=t.coverages,
        plafond_tnd=plafond,
        franchise_tnd=franchise,
        prime_annuelle_tnd=prem["premium"],
        breakdown=prem["breakdown"],
        decision_reasons=decision_reasons,
        flags=flags,
    )
