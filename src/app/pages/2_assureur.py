import os
import requests
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from src.common.ui import apply_branding, render_status
import sys
from pathlib import Path
from src.llm.explainer import OfferExplainer


ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))


apply_branding(show_top_header=False)
# ========== LLM + Explainability helpers (paste here) ==========

def build_client_profile_from_request(req: dict) -> dict:
    sec = req.get("security") or {}
    out = dict(req)
    out["security_alarm"] = bool(sec.get("has_alarm", False))
    out["security_camera"] = bool(sec.get("has_camera", False))
    out["fire_extinguisher"] = bool(sec.get("has_extinguisher", False))
    out["open_at_night"] = bool(out.get("open_at_night", False))
    return out


def get_decision_reasons(detail: dict) -> list:
    aiq = detail.get("ai_quote") or {}
    decision = aiq.get("decision") or {}
    reasons = decision.get("reasons") or []
    return reasons if isinstance(reasons, list) else []


def show_offer_badges(breakdown: dict):
    cols = st.columns(3)

    if float(breakdown.get("budget_unmet", 0.0)) == 1.0:
        cols[0].warning("Budget non atteint")
    else:
        cols[0].info("Budget OK")

    if float(breakdown.get("min_premium_applied", 0.0)) == 1.0:
        cols[1].warning("Prime minimale appliquée")
    else:
        cols[1].info("Prime sans plancher")

    if float(breakdown.get("uncertainty_fallback_used", 0.0)) == 1.0:
        cols[2].warning("Incertitude: mode fallback")
    else:
        cols[2].info("Incertitude: modèle disponible")


def render_explanations_block(
    offer: dict,
    client_profile: dict,
    decision_reasons: list,
    audience: str,  # "customer" ou "insurer"
):
    """
    audience="customer" -> montre Client + Reco
    audience="insurer"  -> montre Assureur + Reco
    """
    offer_for_llm = dict(offer)
    offer_for_llm["decision_reasons"] = decision_reasons

    api_key = os.getenv("GOOGLE_API_KEY")  # optionnel
    explainer = OfferExplainer(api_key=api_key)

    breakdown = offer_for_llm.get("breakdown", {}) or {}
    ml_outputs = {
        "segment_name": "N/A",
        "uncertainty_score": breakdown.get("uncertainty_score", None),
    }

    out = explainer.generate_explanations(
        offer=offer_for_llm,
        client_profile=client_profile,
        ml_outputs=ml_outputs,
    )

    if audience == "customer":
        t1, t2 = st.tabs(["🧾 Explication client", "💡 Recommandations"])
        with t1:
            st.write(out.customer_explanation)
        with t2:
            st.write(out.recommendations)

    elif audience == "insurer":
        t1, t2 = st.tabs(["🔍 Analyse assureur", "💡 Recommandations"])
        with t1:
            st.write(out.insurer_explanation)
        with t2:
            st.write(out.recommendations)

    else:
        # fallback safe
        st.write(out.customer_explanation)
        st.write(out.insurer_explanation)
        st.write(out.recommendations)

    st.caption(out.disclaimer)

load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def api_get(path: str):
    r = requests.get(f"{API_BASE_URL}{path}", timeout=30)
    r.raise_for_status()
    return r.json()


def api_post(path: str, payload=None):
    r = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


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
    return iso.replace("T", " ").replace("Z", "")[:16]


st.header("Espace assureur")
st.caption("Traitement des demandes : génération AI, validation, modification, rejet.")

# Load pending + AI_PROPOSED
try:
    rows = api_get("/requests/pending")
except Exception as e:
    st.error(f"API indisponible : {e}")
    st.stop()

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
            "Nuit": bool(req.get("open_at_night", False)),
        }
    )


df = pd.DataFrame(table)

st.subheader("Demandes à traiter")

if df.empty:
    st.write("Aucune demande en attente.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

st.dataframe(df, hide_index=True, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

selected_id = st.selectbox("Sélectionner une demande", df["ID"].tolist())
detail = api_get(f"/requests/{selected_id}")

st.subheader("Actions")

c1, c2 = st.columns([2, 3])
with c1:
    st.write("Statut :")
    render_status(detail.get("status", ""))

with c2:
    open_proc = st.button("Voir traitement", type="primary", use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)


if open_proc:
    @st.dialog("Traitement de la demande")
    def process_dialog():
        # Reload inside dialog to ensure fresh
        d = api_get(f"/requests/{selected_id}")
        status = d.get("status", "")

        st.markdown(
            """
            <div style="border-left:4px solid #c5172e; padding-left:12px; margin-bottom:12px;">
              <strong>Analyse et décision</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("Statut :")
        render_status(status)

        st.divider()
        st.subheader("Formulaire (lecture seule)")
        st.json(d.get("request", {}))

        st.divider()
        st.subheader("Proposition AI")

        ai_quote = d.get("ai_quote")

        if not ai_quote:
            st.write("Aucune proposition AI n'a été générée pour cette demande.")
            if st.button("Générer offre AI", type="primary", use_container_width=True):
                try:
                    api_post(f"/requests/{selected_id}/ai_offer")
                    st.success("Offre AI générée.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur API : {e}")
            return

        decision_ai = ai_quote.get("decision") or {}
        offer_ai = ai_quote.get("offer") or {}

        st.caption("Décision (règles)")
        st.json(decision_ai)

        k1, k2, k3 = st.columns(3)
        k1.metric("Prime (TND)", f"{offer_ai.get('prime_annuelle_tnd', 0):.2f}")
        k2.metric("Plafond (TND)", f"{offer_ai.get('plafond_tnd', '-')}")
        k3.metric("Franchise (TND)", f"{offer_ai.get('franchise_tnd', '-')}")
        st.divider()
        st.subheader("Explications (AI non décisionnelle)")

        req_obj = d.get("request") or {}
        client_profile = build_client_profile_from_request(req_obj)
        decision_reasons = decision_ai.get("reasons") or []
        if not isinstance(decision_reasons, list):
            decision_reasons = []

        breakdown = offer_ai.get("breakdown", {}) or {}
        show_offer_badges(breakdown)

        render_explanations_block(
            offer=offer_ai,
            client_profile=client_profile,
            decision_reasons=decision_reasons,
            audience="insurer",
        )


        st.divider()
        st.subheader("Décision assureur")

        action_label = st.radio("Action", ["Accepter", "Modifier", "Rejeter"], horizontal=True)
        notes = st.text_area("Notes (optionnel)", value="")

        action_map = {"Accepter": "ACCEPT", "Modifier": "MODIFY", "Rejeter": "REJECT"}
        action = action_map[action_label]

        final_offer = None
        disabled = (action == "ACCEPT")

        if action in {"ACCEPT", "MODIFY"}:
            st.caption("En mode 'Accepter' les champs sont verrouillés. En 'Modifier' ils sont éditables.")

            prime = st.number_input(
                "Prime annuelle (TND)",
                min_value=0.0,
                value=float(offer_ai.get("prime_annuelle_tnd", 0.0)),
                step=10.0,
                disabled=disabled,
            )
            plafond = st.number_input(
                "Plafond (TND)",
                min_value=0.0,
                value=float(offer_ai.get("plafond_tnd", 0.0)),
                step=100.0,
                disabled=disabled,
            )
            franchise = st.number_input(
                "Franchise (TND)",
                min_value=0.0,
                value=float(offer_ai.get("franchise_tnd", 0.0)),
                step=50.0,
                disabled=disabled,
            )

            final_offer = {
                "template_id": offer_ai.get("template_id", ""),
                "template_name": offer_ai.get("template_name", ""),
                "coverages": offer_ai.get("coverages", []),
                "plafond_tnd": float(plafond),
                "franchise_tnd": float(franchise),
                "prime_annuelle_tnd": float(prime),
                "breakdown": offer_ai.get("breakdown", {}),
            }

        st.divider()
        if st.button("Terminer", type="primary", use_container_width=True):
            try:
                payload = {
                    "action": action,
                    "final_offer": final_offer,
                    "processed_by": "demo_assureur",
                    "notes": notes,
                }
                api_post(f"/requests/{selected_id}/finalize", payload=payload)
                st.success("Demande traitée.")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur API : {e}")

    process_dialog()
