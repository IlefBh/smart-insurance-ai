import streamlit as st

# ✅ MUST be the first Streamlit call in the file
st.set_page_config(
    page_title="سالمة",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------ Constants (Frontend only) ------------------
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

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def compute_risk_hint(area_m2, years_active, assets_tnd, revenue_bucket, security_score):
    r_map = {"low": 1.2, "medium": 2.2, "high": 3.2}
    score = 0.0
    score += clamp(area_m2 / 80.0, 0, 3.0)
    score += clamp(assets_tnd / 60000.0, 0, 3.0)
    score += r_map[revenue_bucket]
    score += 0.8 if years_active < 1 else 0.0
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
        reasons = ["risk_low", "basic_protection_sufficient", "security_ok"]
    elif risk < 5.5:
        tid = "T3_NIGHT"
        reasons = ["risk_medium", "theft_cash_exposure", "template_balanced"]
    else:
        tid = "T2_EXTENDED"
        reasons = ["risk_high", "higher_assets_exposure", "need_extended_coverages"]

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
            "risk_hint": round(risk, 2),
            "base": base,
            "risk_loading": round(risk_loading, 2),
            "security_discount_factor": round(security_discount, 3),
        }
    }

# ------------------ UI ------------------
st.title("🛡️ سالمة")
st.caption("Frontend only (mock) — Micro-assurance inclusive pour petits commerçants (Tunisie)")

# Sidebar
st.sidebar.header("Navigation (single-file)")
st.sidebar.write("Pour l’instant : une seule page (Assuré + résultat).")
st.sidebar.markdown("---")
st.sidebar.info("Backend OFF — devis simulé.")

# Layout: form left, quote right
left, right = st.columns([1.05, 0.95], gap="large")

with left:
    st.subheader("🧾 Demande de devis — Assuré")
    st.write("Remplis les informations du commerce et clique **Générer devis**.")

    with st.form("assure_form"):
        governorate = st.selectbox("Gouvernorat", GOVERNORATES)

        activity_code = st.selectbox(
            "Type d’activité",
            [a[0] for a in ACTIVITY_TYPES],
            format_func=lambda x: dict(ACTIVITY_TYPES).get(x, x),
        )

        c1, c2 = st.columns(2)
        with c1:
            shop_area_m2 = st.number_input("Surface (m²)", min_value=5.0, max_value=1000.0, value=35.0, step=1.0)
        with c2:
            years_active = st.number_input("Années d’activité", min_value=0, max_value=60, value=3, step=1)

        assets_value_tnd = st.number_input("Valeur des actifs (TND)", min_value=0.0, max_value=500000.0, value=25000.0, step=500.0)

        revenue_bucket = st.selectbox(
            "Bucket de revenu",
            [r[0] for r in REVENUE_BUCKETS],
            format_func=lambda x: dict(REVENUE_BUCKETS).get(x, x),
        )

        budget_constraint_tnd = st.slider("Budget annuel max (TND)", min_value=100.0, max_value=20000.0, value=1200.0, step=50.0)

        st.markdown("### 🔐 Sécurité")
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            has_alarm = st.checkbox("Alarme", value=False)
        with s2:
            has_camera = st.checkbox("Caméras", value=False)
        with s3:
            has_extinguisher = st.checkbox("Extincteur", value=True)
        with s4:
            has_guard = st.checkbox("Agent", value=False)

        submitted = st.form_submit_button("Générer devis (mock)")

    if submitted:
        security_score = int(has_alarm) + int(has_camera) + int(has_extinguisher) + int(has_guard)
        risk_hint = compute_risk_hint(shop_area_m2, years_active, assets_value_tnd, revenue_bucket, security_score)

        profile = {
            "governorate": governorate,
            "activity_type": activity_code,
            "shop_area_m2": float(shop_area_m2),
            "years_active": int(years_active),
            "assets_value_tnd": float(assets_value_tnd),
            "revenue_bucket": revenue_bucket,
            "budget_constraint_tnd": float(budget_constraint_tnd),
            "security": {
                "has_alarm": bool(has_alarm),
                "has_camera": bool(has_camera),
                "has_extinguisher": bool(has_extinguisher),
                "has_guard": bool(has_guard),
            },
            "security_score": security_score,
            "risk_hint": float(risk_hint),
        }

        st.session_state["assure_profile"] = profile
        st.session_state["mock_quote"] = build_mock_quote(profile)

        st.success("✅ Devis mock généré (affiché à droite).")

    with st.expander("👤 Voir le profil (debug)"):
        st.json(st.session_state.get("assure_profile", {}))

with right:
    st.subheader("✅ Offre recommandée (mock)")

    if "mock_quote" not in st.session_state:
        st.info("Remplis le formulaire puis clique **Générer devis (mock)**.")
    else:
        q = st.session_state["mock_quote"]

        k1, k2, k3 = st.columns(3)
        k1.metric("Prime annuelle (TND)", f"{q['prime_annuelle_tnd']:.2f}")
        k2.metric("Plafond (TND)", f"{q['plafond_tnd']}")
        k3.metric("Franchise (TND)", f"{q['franchise_tnd']}")

        st.write(f"**Produit:** `{q['template_id']}` — **{q['template_name']}**")
        st.write("**Garanties:** " + ", ".join(q["coverages"]))

        st.markdown("### 🧠 Explications")
        for r in q.get("reasons", []):
            st.write(f"- {r}")

        with st.expander("🔎 Détails pricing (breakdown)"):
            st.json(q.get("breakdown", {}))

        with st.expander("📄 Devis complet JSON"):
            st.json(q)

st.markdown("---")
st.caption("Note: Ce devis est simulé (mock). Dans la version finale, il sera fourni par /quote (FastAPI).")
