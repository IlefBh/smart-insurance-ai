import streamlit as st

st.set_page_config(
    page_title="Smart Insurance AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🛡️ Smart Insurance AI")
st.caption("Micro-assurance inclusive pour petits commerçants (Tunisie) — UI + Mock/API mode.")

st.sidebar.markdown("## Navigation")
st.sidebar.caption("Utilise le menu Streamlit **Pages** pour accéder à : Assuré / Assureur / Résultat.")
st.sidebar.markdown("---")
st.sidebar.info("Tip: Active/désactive l’API depuis la page **Assuré**.")
