import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Smart Insurance AI",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* ---------- GLOBAL ---------- */
    html, body, [class*="css"] {
        font-family: 'Inter', 'Segoe UI', sans-serif;
        color: #161616;
        background-color: #eeeeee;
    }

    .main {
        background-color: #eeeeee;
    }

    /* ---------- TITLES ---------- */
    h1, h2, h3 {
        color: #161616;
        font-weight: 600;
    }

    /* ---------- PRIMARY BUTTON ---------- */
    .stButton > button {
        background-color: #c5172e;
        color: white;
        border-radius: 6px;
        border: none;
        padding: 0.45rem 1.1rem;
        font-weight: 500;
    }

    .stButton > button:hover {
        background-color: #a81426;
        color: white;
    }

    /* ---------- SECONDARY / DISABLED ---------- */
    button:disabled {
        background-color: #dddddd !important;
        color: #777777 !important;
    }

    /* ---------- CARDS ---------- */
    .card {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #dddddd;
        margin-bottom: 12px;
    }

    /* ---------- STATUS BADGES ---------- */
    .status {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    .status-pending {
        background-color: #e0e0e0;
        color: #161616;
    }

    .status-ai {
        background-color: #c5172e;
        color: white;
    }

    .status-processed {
        background-color: #2e7d32;
        color: white;
    }

    .status-rejected {
        background-color: #8b1e2d;
        color: white;
    }

    /* ---------- TABLES ---------- */
    .stDataFrame {
        background-color: white;
        border-radius: 6px;
        border: 1px solid #dddddd;
    }

    /* ---------- INPUTS ---------- */
    input, textarea, select {
        background-color: white !important;
        color: #161616 !important;
    }

    /* ---------- SIDEBAR ---------- */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #dddddd;
    }

    </style>
    """,
    unsafe_allow_html=True,
)



st.title("Smart Insurance AI")
st.caption("Micro-assurance inclusive pour petits commerçants (Tunisie)")
st.sidebar.write("Utilise le menu Pages : Assuré / Assureur.")
