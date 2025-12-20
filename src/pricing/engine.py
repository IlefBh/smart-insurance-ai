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


def compute_plafond(profile: Dict, t: ProductTemplate) -> float:
    assets = float(profile.get("assets_value_tnd", 0.0) or 0.0)
    # simple deterministic uplift based on assets exposure
    plaf = max(t.plafond_base_tnd, 0.5 * assets)
    return _clamp(plaf, t.plafond_min_tnd, t.plafond_max_tnd)


def compute_franchise(profile: Dict, t: ProductTemplate, risk: Dict) -> float:
    franchise = float(t.franchise_base_tnd)

    # Risk-based deterministic adjustments
    p_claim = float(risk.get("p_claim", 0.0) or 0.0)
    uncertainty = float(risk.get("uncertainty_score", 0.0) or 0.0)

    # Safety features reduce deductible (bonus)
    alarm = int(bool(profile.get("security_alarm", False)))
    camera = int(bool(profile.get("security_camera", False)))
    ext = int(bool(profile.get("fire_extinguisher", False)))

    safety_score = alarm + camera + ext  # 0..3
    franchise *= (1.0 - 0.06 * safety_score)

    # higher freq/uncertainty increase deductible
    if p_claim > 0.15:
        franchise *= 1.15
    if uncertainty > 0.7:
        franchise *= 1.20

    return _clamp(franchise, t.franchise_min_tnd, t.franchise_max_tnd)


def compute_premium(profile: Dict, t: ProductTemplate, risk: Dict, plafond: float, franchise: float) -> Dict:
    """
    Premium is deterministic:
      expected_loss = p_claim * expected_cost
      premium = expected_loss * (1 + expense_margin) + fixed_fee
    and we apply a simple effect of deductible and limit:
      higher franchise -> lower expected payout
      higher plafond -> slightly higher expected payout
    """
    p_claim = float(risk.get("p_claim", 0.0) or 0.0)
    expected_cost = float(risk.get("expected_cost", 0.0) or 0.0)

    base_expected_loss = p_claim * expected_cost

    # deductible reduces expected payout (simple proxy)
    deductible_factor = 1.0 / (1.0 + (franchise / 2000.0))
    # higher limit increases expected payout slightly
    limit_factor = 1.0 + (plafond - t.plafond_base_tnd) / max(t.plafond_base_tnd, 1.0) * 0.10
    limit_factor = max(0.9, min(1.2, limit_factor))

    expected_loss_adj = base_expected_loss * deductible_factor * limit_factor

    fixed_fee = 120.0  # deterministic flat admin fee (TND/year)
    premium = expected_loss_adj * (1.0 + float(t.base_expense_margin)) + fixed_fee

    breakdown = {
        "p_claim": p_claim,
        "expected_cost": expected_cost,
        "base_expected_loss": base_expected_loss,
        "deductible_factor": deductible_factor,
        "limit_factor": limit_factor,
        "expected_loss_adjusted": expected_loss_adj,
        "expense_margin": float(t.base_expense_margin),
        "fixed_fee": fixed_fee,
    }

    return {"premium": float(premium), "breakdown": breakdown}


def apply_budget_constraint(profile: Dict, t: ProductTemplate, risk: Dict, plafond: float, franchise: float) -> Dict:
    """
    If budget_constraint_tnd exists and premium > budget:
    deterministically increase deductible + lower limit within allowed range.
    """
    budget = profile.get("budget_constraint_tnd")
    if budget is None:
        prem_pack = compute_premium(profile, t, risk, plafond, franchise)
        prem_pack["budget_applied"] = False
        return {"plafond": plafond, "franchise": franchise, **prem_pack}

    budget = float(budget or 0.0)
    prem_pack = compute_premium(profile, t, risk, plafond, franchise)
    premium = prem_pack["premium"]

    if budget <= 0:
        prem_pack["budget_applied"] = False
        return {"plafond": plafond, "franchise": franchise, **prem_pack}

    if premium <= budget:
        prem_pack["budget_applied"] = False
        return {"plafond": plafond, "franchise": franchise, **prem_pack}

    # Try to fit budget by moving within template constraints
    cur_plaf = plafond
    cur_fran = franchise

    for _ in range(30):
        # Step 1: increase deductible (up to max)
        if cur_fran < t.franchise_max_tnd:
            cur_fran = min(t.franchise_max_tnd, cur_fran * 1.10)

        # Step 2: reduce limit (down to min)
        if cur_plaf > t.plafond_min_tnd:
            cur_plaf = max(t.plafond_min_tnd, cur_plaf * 0.95)

        prem_pack = compute_premium(profile, t, risk, cur_plaf, cur_fran)
        if prem_pack["premium"] <= budget:
            prem_pack["budget_applied"] = True
            prem_pack["budget_target"] = budget
            return {"plafond": cur_plaf, "franchise": cur_fran, **prem_pack}

        # cannot adjust further
        if cur_fran >= t.franchise_max_tnd and cur_plaf <= t.plafond_min_tnd:
            break

    prem_pack["budget_applied"] = True
    prem_pack["budget_target"] = budget
    prem_pack["budget_unmet"] = True
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
    breakdown["budget_applied"] = bool(adjusted.get("budget_applied", False))
    if adjusted.get("budget_unmet"):
        breakdown["budget_unmet"] = True
        breakdown["budget_target"] = float(adjusted.get("budget_target", 0.0))

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