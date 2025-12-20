from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.schemas import QuoteRequest, QuoteResponse, SelectionDecision, Offer


app = FastAPI(title="Smart Insurance AI API", version="0.1.0")

# CORS: autorise Streamlit (même machine)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en prod: restreindre
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMPLATES = {
    "T1_ESSENTIEL": {
        "name": "Essential Basic",
        "coverages": ["incendie_basic", "degats_eaux_basic"],
    },
    "T3_NIGHT": {
        "name": "Night & Cash Risk",
        "coverages": ["vol_etendu", "cash_on_premises", "vandalisme"],
    },
    "T2_EXTENDED": {
        "name": "Extended Multi-Risk",
        "coverages": ["incendie_etendu", "vol_etendu", "degats_eaux", "perte_exploitation"],
    },
}


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def compute_risk_hint(req: QuoteRequest) -> float:
    r_map = {"low": 1.2, "medium": 2.2, "high": 3.2}

    security_score = (
        int(req.security.has_alarm)
        + int(req.security.has_camera)
        + int(req.security.has_extinguisher)
        + int(req.security.has_guard)
    )

    score = 0.0
    score += clamp(req.shop_area_m2 / 80.0, 0, 3.0)
    score += clamp(req.assets_value_tnd / 60000.0, 0, 3.0)
    score += r_map.get(req.revenue_bucket, 2.2)

    # jeune activité => un peu plus risquée
    score += 0.8 if req.years_active < 1 else 0.0

    # ouverture nocturne => risque accru
    if req.open_at_night:
        score += 1.2

    # sécurité réduit le risque
    score -= 0.6 * security_score

    return clamp(score, 0.0, 10.0)


def select_template(risk: float, open_at_night: bool) -> tuple[str, list[str], list[str]]:
    candidates = ["T1_ESSENTIEL", "T3_NIGHT", "T2_EXTENDED"]
    reasons: list[str] = []

    if risk < 2.8:
        tid = "T1_ESSENTIEL"
        reasons += ["risk_low", "basic_protection_sufficient"]
    elif risk < 5.5:
        tid = "T3_NIGHT"
        reasons += ["risk_medium", "theft_cash_exposure"]
    else:
        tid = "T2_EXTENDED"
        reasons += ["risk_high", "need_extended_coverages"]

    if open_at_night:
        reasons.append("rule_open_at_night")

    return tid, candidates, reasons


def price_offer(risk: float, security_score: int) -> dict:
    base = 380.0
    risk_loading = risk * 110.0

    security_discount = 1.0 - (security_score * 0.05)
    security_discount = clamp(security_discount, 0.75, 1.0)

    prime = (base + risk_loading) * security_discount
    plafond = float(int(18000 + risk * 9000))
    franchise = float(int(400 + risk * 220))

    breakdown = {
        "risk_hint": round(risk, 2),
        "base": base,
        "risk_loading": round(risk_loading, 2),
        "security_discount_factor": round(security_discount, 3),
    }
    return {
        "prime_annuelle_tnd": round(prime, 2),
        "plafond_tnd": plafond,
        "franchise_tnd": franchise,
        "breakdown": breakdown,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/quote", response_model=QuoteResponse)
def quote(req: QuoteRequest):
    # 1) risk proxy (sera remplacé par tes modèles freq/sev/uncertainty)
    risk = compute_risk_hint(req)

    security_score = (
        int(req.security.has_alarm)
        + int(req.security.has_camera)
        + int(req.security.has_extinguisher)
        + int(req.security.has_guard)
    )

    # 2) template selection (business rules)
    template_id, candidates, reasons = select_template(risk=risk, open_at_night=req.open_at_night)

    # 3) pricing (actuarial-style)
    priced = price_offer(risk=risk, security_score=security_score)

    tpl = TEMPLATES[template_id]

    decision = SelectionDecision(
        template_id=template_id,
        candidates=candidates,
        reasons=reasons,
    )

    offer = Offer(
        template_id=template_id,
        template_name=tpl["name"],
        coverages=tpl["coverages"],
        plafond_tnd=priced["plafond_tnd"],
        franchise_tnd=priced["franchise_tnd"],
        prime_annuelle_tnd=priced["prime_annuelle_tnd"],
        breakdown=priced["breakdown"],
    )

    return QuoteResponse(decision=decision, offer=offer)
