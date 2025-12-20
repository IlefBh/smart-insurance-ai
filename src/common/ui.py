import streamlit as st

def render_status(status: str):
    cls = {
        "PENDING": "status status-pending",
        "AI_PROPOSED": "status status-ai",
        "PROCESSED": "status status-processed",
        "REJECTED": "status status-rejected",
    }.get(status, "status")

    st.markdown(
        f'<span class="{cls}">{status}</span>',
        unsafe_allow_html=True,
    )
