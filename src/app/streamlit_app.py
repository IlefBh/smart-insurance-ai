import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

import streamlit as st
from src.common.ui import apply_branding

st.set_page_config(
    page_title="سالمة",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_branding(show_top_header=True)


st.markdown("</div>", unsafe_allow_html=True)
