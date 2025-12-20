import streamlit as st

st.title("✅ Résultat — Offre recommandée")
st.caption("Affichage côté assuré : lisible, actionnable, transparent.")

if "mock_quote" not in st.session_state:
    st.warning("Aucun devis disponible. Va sur **Assuré** puis génère un devis.")
    st.stop()

quote = st.session_state["mock_quote"]
source = st.session_state.get("quote_source", "mock")

k1, k2, k3 = st.columns(3)
k1.metric("Prime annuelle (TND)", f"{quote.get('prime_annuelle_tnd',0):.2f}")
k2.metric("Plafond (TND)", f"{quote.get('plafond_tnd','-')}")
k3.metric("Franchise (TND)", f"{quote.get('franchise_tnd','-')}")

st.markdown("### 🧩 Produit")
st.write(f"**{quote.get('template_name','-')}** (`{quote.get('template_id','-')}`)")
cov = quote.get("coverages", [])
if cov:
    st.write("**Garanties incluses:** " + ", ".join(cov))
else:
    st.info("Garanties non fournies par la réponse (à compléter côté API ou mock).")

st.markdown("### 🧠 Pourquoi cette offre ?")
reasons = quote.get("reasons", [])
if reasons:
    for r in reasons:
        st.write(f"- {r}")
else:
    st.info("Aucune explication fournie. Active `decision.reasons` côté backend.")

st.caption(f"Source devis: {source.upper()}")

with st.expander("📄 JSON complet (debug)"):
    st.json(quote)
