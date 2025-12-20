import streamlit as st

st.title("🏢 Assureur — Backoffice")
st.caption("Vue audit/jury-friendly : décision, paramètres, justification.")

if "mock_quote" not in st.session_state:
    st.warning("Aucun devis en session. Va d’abord sur **Assuré**.")
    st.stop()

quote = st.session_state["mock_quote"]
profile = st.session_state.get("assure_profile", {})
source = st.session_state.get("quote_source", "mock")

st.markdown(f"**Source devis:** `{source}`")

st.subheader("📌 Décision")
st.write(f"**Template:** `{quote.get('template_id','?')}` — {quote.get('template_name','?')}")
st.write("**Raisons:**")
for r in quote.get("reasons", []):
    st.write(f"- {r}")

st.subheader("📊 KPI pricing")
k1, k2, k3 = st.columns(3)
k1.metric("Prime annuelle (TND)", f"{quote.get('prime_annuelle_tnd',0):.2f}")
k2.metric("Plafond (TND)", f"{quote.get('plafond_tnd','-')}")
k3.metric("Franchise (TND)", f"{quote.get('franchise_tnd','-')}")

st.subheader("🔍 Profil assuré (audit)")
with st.expander("Voir profil complet"):
    st.json(profile)

with st.expander("Breakdown / détails"):
    st.json(quote.get("breakdown", {}))

with st.expander("JSON devis complet"):
    st.json(quote)
