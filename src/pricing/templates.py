# src/pricing/templates.py
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ProductTemplate:
    id: str
    name: str
    coverages: List[str]

    # eligibility constraints (simple + explainable)
    activity_in: Optional[List[str]] = None
    open_at_night_required: Optional[bool] = None
    assets_min_tnd: Optional[float] = None
    assets_max_tnd: Optional[float] = None

    # configurable ranges
    plafond_base_tnd: float = 30000
    plafond_min_tnd: float = 15000
    plafond_max_tnd: float = 50000

    franchise_base_tnd: float = 1000
    franchise_min_tnd: float = 500
    franchise_max_tnd: float = 3000

    # pricing policy
    base_expense_margin: float = 0.35  # 35% (expenses + margin baseline)


TEMPLATES: Dict[str, ProductTemplate] = {
    "T1_ESSENTIEL": ProductTemplate(
        id="T1_ESSENTIEL",
        name="Commerce Essentiel",
        coverages=["fire", "theft_basic", "water_damage"],
        activity_in=["grocery", "clothing", "other"],
        assets_max_tnd=60000,
        plafond_base_tnd=30000,
        plafond_min_tnd=15000,
        plafond_max_tnd=50000,
        franchise_base_tnd=1000,
        franchise_min_tnd=500,
        franchise_max_tnd=3000,
        base_expense_margin=0.35,
    ),
    "T2_PLUS": ProductTemplate(
        id="T2_PLUS",
        name="Commerce Plus",
        coverages=["fire", "theft_extended", "water_damage", "business_interruption"],
        activity_in=["pharmacy", "electronics"],
        assets_min_tnd=30000,
        plafond_base_tnd=60000,
        plafond_min_tnd=40000,
        plafond_max_tnd=120000,
        franchise_base_tnd=2000,
        franchise_min_tnd=1000,
        franchise_max_tnd=6000,
        base_expense_margin=0.40,
    ),
    "T3_NIGHT": ProductTemplate(
        id="T3_NIGHT",
        name="Night & Cash Risk",
        coverages=["theft_extended", "cash_on_premises", "vandalism"],
        open_at_night_required=True,
        plafond_base_tnd=25000,
        plafond_min_tnd=15000,
        plafond_max_tnd=60000,
        franchise_base_tnd=1500,
        franchise_min_tnd=800,
        franchise_max_tnd=5000,
        base_expense_margin=0.45,
    ),
}
