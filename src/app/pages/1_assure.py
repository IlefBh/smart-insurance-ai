import os
import requests
import streamlit as st

# ------------------ API config ------------------
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

# ------------------ Constants ------------------
GOVERNORATES = [
    "Tunis", "Ariana", "Ben Arous", "Manouba", "Nabeul", "Bizerte",
    "Sousse", "Monastir", "Mahdia", "Kairouan", "Sfax", "Gabès", "Médenine", "Gafsa", "Autre"
]

ACTIVITY_TYPES = [
    ("grocery", "Épicerie"),
    ("cafe", "Café"),
    ("pharmacy", "Pharmacie"),
    ("clothing", "Vêtements"),
    ("electronics", "Électronique"),
    ("kiosk", "Kiosque"),
    ("restaurant", "Restaurant"),
    ("other", "Autre"),
]

REVENUE_BUCKETS = [("low", "Faible"), ("medium", "Moyen"), ("high", "Élevé")]

TEMPLATES = {
    "T1_ESSENTIEL": {"name": "Essential Basic", "coverages": ["incendie_basic", "degats_eaux_basic"]},
    "T3_NIGHT": {"name": "Night & Cash Risk", "coverages": ["vol_etendu", "cash_on_premises", "vandalisme"]},
    "T2_EXTENDED": {"name": "Extended Multi-Risk", "coverages": ["incendie_etendu", "vol_etendu", "degats_eaux", "perte_exploitation"]},
}

# ------------------ Sidebar mode ------------------
st.sidebar.header("⚙️ Mode")
use_api = st.sidebar.toggle("Utiliser l’API /quote", value=False)
st.sidebar.caption("OFF = mode mock (frontend only) • ON = POST vers FastAPI")
st.sidebar.write("API_BASE_URL:", API_BASE_URL)

# ------------------ Helpers ------------------
def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def compute_risk_hint(area_m2, years_active, assets_tnd, revenue_bucket, security_score, open_at_night):
    r_map = {"low": 1.2, "medium": 2.2, "high": 3.2}
    score = 0.0

    score += clamp(area_m2 / 80.0, 0, 3.0)
    score += clamp(assets_tnd / 60000.0, 0, 3.0)
    score += r_map[revenue_bucket]

    score += 0.8 if years_active < 1 else 0.0

    if open_at_night:
        score += 1.2

    score -= 0.6 * security_score

    return clamp(score, 0.0, 10.0)

def build_mock_quote(profile):
    risk = profile["risk_hint"]
    base = 380.0
    risk_loading = risk * 110.0

    security_discount = 1.0 - (profile["security_score"] * 0.05)
    security_discount = clamp(security_discount, 0.75, 1.0)

    prime = (base + risk_loading) * security_discount
    plafond = int(18000 + risk * 9000)
    franchise = int(400 + risk * 220)

    if risk < 2.8:
        tid = "T1_ESSENTIEL"
        reasons = ["Risque faible", "Protection de base suffisante", "Bon niveau de sécurité"]
    elif risk < 5.5:
        tid = "T3_NIGHT"
        reasons = ["Risque modéré", "Exposition au vol et cash", "Équilibre couverture / prix"]
    else:
        tid = "T2_EXTENDED"
        reasons = ["Risque élevé", "Actifs importants", "Couverture étendue recommandée"]

    if profile.get("open_at_night"):
        reasons.append("Ouverture nocturne → exposition accrue au vol / vandalisme")

    t = TEMPLATES[tid]
    return {
        "template_id": tid,
        "template_name": t["name"],
        "coverages": t["coverages"],
        "prime_annuelle_tnd": round(prime, 2),
        "plafond_tnd": plafond,
        "franchise_tnd": franchise,
        "reasons": reasons,
        "breakdown": {
            "indice_risque": round(risk, 2),
            "base": base,
            "chargement_risque": round(risk_loading, 2),
            "facteur_securite": round(security_discount, 3),
            "open_at_night": bool(profile.get("open_at_night")),
        }
    }

def build_payload(profile: dict) -> dict:
    return {
        "governorate": profile["governorate"],
        "activity_type": profile["activity_type"],
        "shop_area_m2": profile["shop_area_m2"],
        "years_active": profile["years_active"],
        "assets_value_tnd": profile["assets_value_tnd"],
        "revenue_bucket": profile["revenue_bucket"],
        "security": {
            "has_alarm": profile.get("has_alarm", False),
            "has_camera": profile.get("has_camera", False),
            "has_extinguisher": profile.get("has_extinguisher", False),
            "has_guard": profile.get("has_guard", False),
        },
        "open_at_night": profile.get("open_at_night", False),
        "budget_constraint_tnd": profile["budget_constraint_tnd"],
    }

def call_quote_api(payload: dict) -> dict:
    url = f"{API_BASE_URL}/quote"
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def normalize_api_response(api_resp: dict) -> dict:
    """
    Normalize API response to the UI quote format.
    Expected API response (common): { decision: {...}, offer: {...} }
    """
    if "offer" in api_resp:
        offer = api_resp["offer"]
        decision = api_resp.get("decision", {})
        reasons = decision.get("reasons", [])
        # keep reasons on offer so UI pages can reuse it
        offer["reasons"] = reasons
        return offer
    return api_resp

# ------------------ Light CSS ------------------
st.markdown(
    """
    <style>
      .hero {
        padding: 18px;
        border-radius: 16px;
        background: linear-gradient(135deg, rgba(58,123,213,0.18), rgba(0,210,255,0.10));
        border: 1px solid rgba(255,255,255,0.12);
        margin-bottom: 1.2rem;
      }
      .card {
        padding: 14px;
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,0.12);
        background: rgba(255,255,255,0.03);
        margin-bottom: 1rem;
      }
      .muted { opacity: 0.85; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------ Hero ------------------
st.markdown(
    """
    <div class="hero">
      <h2>🧾 Assuré — Demande de devis</h2>
      <p class="muted">
        Obtenez une <b>offre personnalisée</b> (prime, plafond, franchise) avec des <b>explications claires</b>.
        <br/>Mode démonstration: mock ou API selon le toggle.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ------------------ Form ------------------
with st.form("assure_form"):
    left, right = st.columns(2, gap="large")

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🏪 Informations sur le commerce")
        governorate = st.selectbox("Gouvernorat", GOVERNORATES)
        activity_code = st.selectbox(
            "Type d’activité",
            [a[0] for a in ACTIVITY_TYPES],
            format_func=lambda x: dict(ACTIVITY_TYPES).get(x, x),
        )
        shop_area_m2 = st.number_input("Surface du local (m²)", 5.0, 1000.0, 35.0, 1.0)
        years_active = st.number_input("Années d’activité", 0, 60, 3, 1)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("💰 Données financières")
        assets_value_tnd = st.number_input("Valeur des actifs (TND)", 0.0, 500000.0, 25000.0, 500.0)
        revenue_bucket = st.selectbox(
            "Niveau de revenu",
            [r[0] for r in REVENUE_BUCKETS],
            format_func=lambda x: dict(REVENUE_BUCKETS).get(x, x),
        )
        budget_constraint_tnd = st.slider("Budget annuel maximum (TND)", 100.0, 20000.0, 1200.0, 50.0)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🔐 Sécurité du local")
    s1, s2, s3, s4, s5 = st.columns(5)
    with s1:
        has_alarm = st.checkbox("Alarme")
    with s2:
        has_camera = st.checkbox("Caméras")
    with s3:
        has_extinguisher = st.checkbox("Extincteur", value=True)
    with s4:
        has_guard = st.checkbox("Agent de sécurité")
    with s5:
        open_at_night = st.checkbox("Ouvert la nuit 🌙")
    st.markdown("</div>", unsafe_allow_html=True)

    submitted = st.form_submit_button("🔍 Générer mon devis")

# ------------------ Result ------------------
if submitted:
    security_score = int(has_alarm) + int(has_camera) + int(has_extinguisher) + int(has_guard)

    risk_hint = compute_risk_hint(
        shop_area_m2,
        years_active,
        assets_value_tnd,
        revenue_bucket,
        security_score,
        open_at_night,
    )

    profile = {
        "governorate": governorate,
        "activity_type": activity_code,
        "shop_area_m2": float(shop_area_m2),
        "years_active": int(years_active),
        "assets_value_tnd": float(assets_value_tnd),
        "revenue_bucket": revenue_bucket,
        "budget_constraint_tnd": float(budget_constraint_tnd),
        "security_score": security_score,
        "has_alarm": bool(has_alarm),
        "has_camera": bool(has_camera),
        "has_extinguisher": bool(has_extinguisher),
        "has_guard": bool(has_guard),
        "open_at_night": bool(open_at_night),
        "risk_hint": float(risk_hint),
    }

    st.session_state["assure_profile"] = profile

    payload = build_payload(profile)

    if use_api:
        try:
            with st.spinner("Appel API /quote…"):
                api_resp = call_quote_api(payload)
            quote = normalize_api_response(api_resp)
            st.session_state["mock_quote"] = quote
            st.session_state["quote_source"] = "api"
            st.success("✅ Devis généré via API. Consultez l’onglet **Résultat**.")
        except Exception as e:
            st.warning(f"API indisponible: {e}. Fallback en mode mock.")
            quote = build_mock_quote(profile)
            st.session_state["mock_quote"] = quote
            st.session_state["quote_source"] = "mock"
            st.success("✅ Devis généré (mock). Consultez l’onglet **Résultat**.")
    else:
        quote = build_mock_quote(profile)
        st.session_state["mock_quote"] = quote
        st.session_state["quote_source"] = "mock"
        st.success("✅ Devis généré (mock). Consultez l’onglet **Résultat**.")

    # Quick preview
    c1, c2, c3 = st.columns(3)
    c1.metric("Indice risque", f"{risk_hint:.2f}")
    c2.metric("Prime (TND)", f"{st.session_state['mock_quote'].get('prime_annuelle_tnd', 0):.2f}")
    c3.metric("Source", st.session_state.get("quote_source", "mock").upper())

    with st.expander("📦 Payload envoyé (debug)"):
        st.json(payload)
