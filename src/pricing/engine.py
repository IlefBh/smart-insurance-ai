# src/pricing/engine.py
from dataclasses import dataclass
from typing import Dict, List

from .templates import ProductTemplate, TEMPLATES
from .rules import SelectionDecision


@dataclass
class Offer:
    template_id: str
    template_name: str
    coverages: List[str]
    plafond_tnd: float
    franchise_tnd: float
    prime_annuelle_tnd: float
    breakdown: Dict[str, float]

    decision_reasons: List[str]
    flags: Dict


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _min_premium_for_template(t: ProductTemplate) -> float:
    """
    Hackathon-grade deterministic minimum premium per template.
    Keeps the offer realistic (avoid absurdly low premiums).
    """
    if t.id == "T2_PLUS":
        return 500.0
    if t.id == "T3_NIGHT":
        return 550.0
    return 250.0  # T1_ESS


def compute_plafond(profile: Dict, t: ProductTemplate) -> float:
    assets = float(profile.get("assets_value_tnd", 0.0) or 0.0)
    plaf = max(t.plafond_base_tnd, 0.5 * assets)
    return _clamp(plaf, t.plafond_min_tnd, t.plafond_max_tnd)


def compute_franchise(profile: Dict, t: ProductTemplate, risk: Dict) -> float:
    franchise = float(t.franchise_base_tnd)

    p_claim = float(risk.get("p_claim", 0.0) or 0.0)
    uncertainty = float(risk.get("uncertainty_score", 0.0) or 0.0)

    alarm = int(bool(profile.get("security_alarm", False)))
    camera = int(bool(profile.get("security_camera", False)))
    ext = int(bool(profile.get("fire_extinguisher", False)))

    safety_score = alarm + camera + ext  # 0..3
    franchise *= (1.0 - 0.06 * safety_score)

    if p_claim > 0.15:
        franchise *= 1.15
    if uncertainty > 0.7:
        franchise *= 1.20

    return _clamp(franchise, t.franchise_min_tnd, t.franchise_max_tnd)


def compute_premium(profile: Dict, t: ProductTemplate, risk: Dict, plafond: float, franchise: float) -> Dict:
    """
    Premium deterministic:
      expected_loss = p_claim * expected_cost
      premium = expected_loss * (1 + expense_margin) + fixed_fee
    with deductible + limit effects, and a deterministic min premium.
    """
    p_claim = float(risk.get("p_claim", 0.0) or 0.0)
    expected_cost = float(risk.get("expected_cost", 0.0) or 0.0)

    base_expected_loss = p_claim * expected_cost

    deductible_factor = 1.0 / (1.0 + (franchise / 2000.0))
    limit_factor = 1.0 + (plafond - t.plafond_base_tnd) / max(t.plafond_base_tnd, 1.0) * 0.10
    limit_factor = max(0.9, min(1.2, limit_factor))

    expected_loss_adj = base_expected_loss * deductible_factor * limit_factor

    fixed_fee = 120.0
    premium_raw = expected_loss_adj * (1.0 + float(t.base_expense_margin)) + fixed_fee

    # ✅ Min premium
    min_premium = _min_premium_for_template(t)
    min_premium_applied = premium_raw < min_premium
    premium = max(premium_raw, min_premium)

    breakdown = {
        "p_claim": p_claim,
        "expected_cost": expected_cost,
        "base_expected_loss": base_expected_loss,
        "deductible_factor": deductible_factor,
        "limit_factor": limit_factor,
        "expected_loss_adjusted": expected_loss_adj,
        "expense_margin": float(t.base_expense_margin),
        "fixed_fee": fixed_fee,
        "min_premium_applied": float(1.0 if min_premium_applied else 0.0),  # keep numeric for Pydantic
        "min_premium_value": float(min_premium),
        "premium_raw": float(premium_raw),
    }

    return {"premium": float(premium), "breakdown": breakdown}


def apply_budget_constraint(profile: Dict, t: ProductTemplate, risk: Dict, plafond: float, franchise: float) -> Dict:
    """
    If budget_constraint_tnd exists and premium > budget:
    deterministically increase deductible + lower limit within allowed range.
    If budget is below min premium, we keep offer but mark budget_unmet.
    """
    budget = profile.get("budget_constraint_tnd")
    if budget is None:
        prem_pack = compute_premium(profile, t, risk, plafond, franchise)
        prem_pack["budget_applied"] = False
        return {"plafond": plafond, "franchise": franchise, **prem_pack}

    budget = float(budget or 0.0)

    prem_pack = compute_premium(profile, t, risk, plafond, franchise)
    premium = float(prem_pack["premium"])

    if budget <= 0:
        prem_pack["budget_applied"] = False
        return {"plafond": plafond, "franchise": franchise, **prem_pack}

    # ✅ If budget is lower than min premium, we cannot meet it.
    min_premium = _min_premium_for_template(t)
    if budget < min_premium:
        prem_pack["budget_applied"] = True
        prem_pack["budget_target"] = budget
        prem_pack["budget_unmet"] = True
        prem_pack["budget_reason"] = "budget_below_min_premium"
        return {"plafond": plafond, "franchise": franchise, **prem_pack}

    if premium <= budget:
        prem_pack["budget_applied"] = False
        return {"plafond": plafond, "franchise": franchise, **prem_pack}

    cur_plaf = float(plafond)
    cur_fran = float(franchise)

    for _ in range(30):
        if cur_fran < t.franchise_max_tnd:
            cur_fran = min(t.franchise_max_tnd, cur_fran * 1.10)

        if cur_plaf > t.plafond_min_tnd:
            cur_plaf = max(t.plafond_min_tnd, cur_plaf * 0.95)

        prem_pack = compute_premium(profile, t, risk, cur_plaf, cur_fran)
        if float(prem_pack["premium"]) <= budget:
            prem_pack["budget_applied"] = True
            prem_pack["budget_target"] = budget
            return {"plafond": cur_plaf, "franchise": cur_fran, **prem_pack}

        if cur_fran >= t.franchise_max_tnd and cur_plaf <= t.plafond_min_tnd:
            break

    prem_pack["budget_applied"] = True
    prem_pack["budget_target"] = budget
    prem_pack["budget_unmet"] = True
    prem_pack["budget_reason"] = "budget_not_reachable_within_constraints"
    return {"plafond": cur_plaf, "franchise": cur_fran, **prem_pack}


def build_offer(profile: Dict, risk: Dict, decision: SelectionDecision) -> Offer:
    t = TEMPLATES[decision.template_id]

    plafond = compute_plafond(profile, t)
    franchise = compute_franchise(profile, t, risk)

    adjusted = apply_budget_constraint(profile, t, risk, plafond, franchise)
    plafond = float(adjusted["plafond"])
    franchise = float(adjusted["franchise"])
    premium = float(adjusted["premium"])
    breakdown = dict(adjusted["breakdown"])

    # ✅ include uncertainty_score (numeric only)
    breakdown["uncertainty_score"] = float(risk.get("uncertainty_score", 0.0) or 0.0)

    breakdown["budget_applied"] = float(1.0 if adjusted.get("budget_applied", False) else 0.0)
    if adjusted.get("budget_unmet"):
        breakdown["budget_unmet"] = float(1.0)
        breakdown["budget_target"] = float(adjusted.get("budget_target", 0.0) or 0.0)

    flags = {
        "underwriting_review": bool(float(risk.get("uncertainty_score", 0.0) or 0.0) > 0.7),
        "high_risk": bool(float(risk.get("p_claim", 0.0) or 0.0) > 0.25),
        "budget_unmet": bool(adjusted.get("budget_unmet", False)),
    }

    return Offer(
        template_id=t.id,
        template_name=t.name,
        coverages=t.coverages,
        plafond_tnd=plafond,
        franchise_tnd=franchise,
        prime_annuelle_tnd=premium,
        breakdown=breakdown,
        decision_reasons=decision.reasons,
        flags=flags,
    )
