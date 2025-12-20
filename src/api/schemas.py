from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


class SecurityFeatures(BaseModel):
    has_alarm: bool = False
    has_camera: bool = False
    has_extinguisher: bool = False


class QuoteRequest(BaseModel):
    governorate: str
    activity_type: str
    shop_area_m2: float = Field(ge=0)
    years_active: int = Field(ge=0)
    assets_value_tnd: float = Field(ge=0)
    revenue_monthly_tnd: float = Field(ge=0)
    security: SecurityFeatures = SecurityFeatures()
    open_at_night: bool = False
    budget_constraint_tnd: float = Field(ge=0)


class SelectionDecision(BaseModel):
    template_id: str
    candidates: List[str] = []
    reasons: List[str] = []


class Offer(BaseModel):
    template_id: str
    template_name: str
    coverages: List[str]
    plafond_tnd: float
    franchise_tnd: float
    prime_annuelle_tnd: float
    breakdown: Dict[str, float] = {}


class QuoteResponse(BaseModel):
    decision: SelectionDecision
    offer: Offer


class FinalizeRequest(BaseModel):
    action: str  # ACCEPT / MODIFY / REJECT
    final_offer: Optional[Dict[str, Any]] = None
    processed_by: str = "demo_assureur"
    notes: Optional[str] = None
