# src/pricing/templates.py
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ProductTemplate:
    id: str
    name: str
    coverages: List[str]

    # Eligibility constraints (simple + explainable)
    activity_in: Optional[List[str]] = None
    open_at_night_required: Optional[bool] = None
    assets_min_tnd: Optional[float] = None
    assets_max_tnd: Optional[float] = None

    # Ranges / bases
    plafond_base_tnd: float = 20000
    plafond_min_tnd: float = 10000
    plafond_max_tnd: float = 60000

    franchise_base_tnd: float = 1000
    franchise_min_tnd: float = 500
    franchise_max_tnd: float = 4000

    # Pricing knobs (deterministic)
    base_expense_margin: float = 0.40  # expenses + margin share


TEMPLATES: Dict[str, ProductTemplate] = {
    "T1_ESS": ProductTemplate(
        id="T1_ESS",
        name="Commerce Essentiel",
        coverages=["fire_basic", "water_damage", "liability_basic", "theft_basic"],
        plafond_base_tnd=20000,
        plafond_min_tnd=10000,
        plafond_max_tnd=40000,
        franchise_base_tnd=800,
        franchise_min_tnd=400,
        franchise_max_tnd=2500,
        base_expense_margin=0.38,
    ),
    "T2_PLUS": ProductTemplate(
        id="T2_PLUS",
        name="Commerce Plus",
        coverages=[
            "fire_extended",
            "water_damage",
            "liability_extended",
            "theft_extended",
            "business_interruption",
        ],
        assets_min_tnd=40000,
        plafond_base_tnd=45000,
        plafond_min_tnd=25000,
        plafond_max_tnd=120000,
        franchise_base_tnd=1200,
        franchise_min_tnd=600,
        franchise_max_tnd=6000,
        base_expense_margin=0.42,
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
