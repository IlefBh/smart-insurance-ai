import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

import os
import requests
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from src.common.ui import apply_branding, render_status



apply_branding(show_top_header=False)


load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

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


# ---------------- API helpers ----------------
def api_get(path: str):
    r = requests.get(f"{API_BASE_URL}{path}", timeout=30)
    r.raise_for_status()
    return r.json()


def api_post(path: str, payload=None):
    r = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


# ---------------- UI helpers ----------------
def render_status(status: str):
    cls = {
        "PENDING": "status status-pending",
        "AI_PROPOSED": "status status-ai",
        "PROCESSED": "status status-processed",
        "REJECTED": "status status-rejected",
    }.get(status, "status")
    st.markdown(f'<span class="{cls}">{status}</span>', unsafe_allow_html=True)


def pretty_dt(iso: str) -> str:
    if not iso:
        return ""
    # "2025-12-20T01:23:45Z" -> "2025-12-20 01:23"
    return iso.replace("T", " ").replace("Z", "")[:16]


st.header("Espace assuré")
st.caption("Création et suivi des demandes de devis.")

# Header actions
left, right = st.columns([2, 3])
with left:
    new_req = st.button("Nouvelle demande", type="primary", use_container_width=True)

with right:
    st.write("")

# Load data
try:
    rows = api_get("/requests?insured_id=demo_user")
except Exception as e:
    st.error(f"API indisponible : {e}")
    st.stop()

# Build table
table = []
for r in rows:
    req = r.get("request") or {}
    table.append(
        {
            "ID": r.get("id"),
            "Date": pretty_dt(r.get("created_at", "")),
            "Statut": r.get("status", ""),
            "Gouvernorat": req.get("governorate", ""),
            "Activité": req.get("activity_type", ""),
            "Actifs (TND)": req.get("assets_value_tnd", 0),
            "Revenu/mois (TND)": req.get("revenue_monthly_tnd", 0),
        }
    )

df = pd.DataFrame(table)

st.subheader("Mes demandes")

if df.empty:
    st.write("Aucune demande pour le moment.")
    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.dataframe(df, hide_index=True, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    selected_id = st.selectbox("Sélectionner une demande", df["ID"].tolist())

    detail = api_get(f"/requests/{selected_id}")
    status = detail.get("status", "PENDING")

    st.subheader("Actions sur la demande")

    c1, c2, c3 = st.columns([2, 2, 4])
    with c1:
        st.write("Statut :")
        render_status(status)

    with c2:
        if st.button("Visualiser", use_container_width=True):
            st.session_state["assure_view_request_id"] = selected_id

    with c3:
        if status == "PROCESSED":
            if st.button("Voir offre", type="primary", use_container_width=True):
                st.session_state["assure_view_offer_id"] = selected_id
        elif status == "REJECTED":
            st.button("Rejetée", disabled=True, use_container_width=True)
        else:
            st.button("Pending", disabled=True, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Dialog: create new request ----------------
if new_req:
    @st.dialog("Nouvelle demande")
    def new_request_dialog():
        st.markdown(
            """
            <div style="border-left:4px solid #c5172e; padding-left:12px; margin-bottom:12px;">
              <strong>Formulaire de demande</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

        left, right = st.columns(2)

        with left:
            governorate = st.selectbox("Gouvernorat", GOVERNORATES)
            activity_code = st.selectbox(
                "Type d’activité",
                [a[0] for a in ACTIVITY_TYPES],
                format_func=lambda x: dict(ACTIVITY_TYPES).get(x, x),
            )
            shop_area_m2 = st.number_input("Surface du local (m²)", 5.0, 1000.0, 35.0, 1.0)
            years_active = st.number_input("Années d’activité", 0, 60, 3, 1)

        with right:
            assets_value_tnd = st.number_input("Valeur des actifs (TND)", 0.0, 500000.0, 25000.0, 500.0)
            revenue_monthly_tnd = st.number_input(
                "Revenu mensuel estimé (TND)",
                min_value=0.0,
                max_value=500000.0,
                value=6000.0,
                step=100.0,
            )

            budget_constraint_tnd = st.slider("Budget annuel maximum (TND)", 100.0, 20000.0, 1200.0, 50.0)

        st.divider()
        st.subheader("Sécurité")
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            has_alarm = st.checkbox("Alarme")
        with s2:
            has_camera = st.checkbox("Caméras")
        with s3:
            has_extinguisher = st.checkbox("Extincteur", value=True)
        with s4:
            open_at_night = st.checkbox("Ouvert la nuit")

        payload = {
            "governorate": governorate,
            "activity_type": activity_code,
            "shop_area_m2": float(shop_area_m2),
            "years_active": int(years_active),
            "assets_value_tnd": float(assets_value_tnd),
            "revenue_monthly_tnd": float(revenue_monthly_tnd),
            "security": {
                "has_alarm": bool(has_alarm),
                "has_camera": bool(has_camera),
                "has_extinguisher": bool(has_extinguisher),
            },
            "open_at_night": bool(open_at_night),
            "budget_constraint_tnd": float(budget_constraint_tnd),
        }

        st.divider()
        if st.button("Soumettre la demande", type="primary", use_container_width=True):
            try:
                api_post("/requests?insured_id=demo_user", payload)
                st.success("Demande créée.")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur API : {e}")

    new_request_dialog()

# ---------------- Dialog: view request ----------------
if st.session_state.get("assure_view_request_id"):
    rid = st.session_state.pop("assure_view_request_id")
    detail = api_get(f"/requests/{rid}")

    @st.dialog("Détails de la demande (lecture seule)")
    def view_request_dialog():
        render_status(detail.get("status", ""))
        st.divider()
        st.json(detail.get("request", {}))
        if detail.get("notes"):
            st.divider()
            st.subheader("Notes")
            st.write(detail["notes"])

    view_request_dialog()

# ---------------- Dialog: view final offer ----------------
if st.session_state.get("assure_view_offer_id"):
    rid = st.session_state.pop("assure_view_offer_id")
    detail = api_get(f"/requests/{rid}")
    offer = detail.get("final_offer")

    @st.dialog("Offre finalisée")
    def view_offer_dialog():
        if not offer:
            st.info("Aucune offre finalisée disponible.")
            return

        st.markdown(
            """
            <div style="border-left:4px solid #c5172e; padding-left:12px; margin-bottom:12px;">
              <strong>Offre recommandée</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Prime annuelle (TND)", f"{offer.get('prime_annuelle_tnd', 0):.2f}")
        c2.metric("Plafond (TND)", f"{offer.get('plafond_tnd', '-')}")
        c3.metric("Franchise (TND)", f"{offer.get('franchise_tnd', '-')}")

        st.divider()
        st.subheader("Produit")
        st.write(offer.get("template_name", "-"))
        cov = offer.get("coverages", [])
        if cov:
            st.write(", ".join(cov))

        st.divider()
        with st.expander("Détails (JSON)"):
            st.json(offer)

    view_offer_dialog()
