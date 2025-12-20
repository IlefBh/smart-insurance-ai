from __future__ import annotations

import streamlit as st
from pathlib import Path


def apply_branding(
    page_title: str = "سالمة",
    slogan: str = "« Parce que votre travail mérite d’être protégé. »",
    show_top_header: bool = True,
) -> None:
    """
    Must be called at the top of EACH Streamlit page (multipage app),
    otherwise CSS + sidebar logo won't persist when switching pages.
    """
    assets_dir = Path(__file__).resolve().parents[1] / "app" / "assets"
    logo_path = assets_dir / "logo.png"

    # Sidebar logo
    if logo_path.exists():
        st.sidebar.image(str(logo_path), use_container_width=True)
    st.sidebar.markdown("---")

    # Global CSS (light theme + palette)
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
            background-color: #c5172e !important;
            color: white !important;
            border-radius: 8px !important;
            border: none !important;
            padding: 0.50rem 1.1rem !important;
            font-weight: 600 !important;
        }

        .stButton > button:hover {
            background-color: #a81426 !important;
            color: white !important;
        }

        /* ---------- SECONDARY / DISABLED ---------- */
        button:disabled {
            background-color: #dddddd !important;
            color: #777777 !important;
        }

        /* ---------- CARDS ---------- */
        .card {
            background-color: #ffffff;
            border-radius: 10px;
            padding: 16px;
            border: 1px solid #dddddd;
            margin-bottom: 12px;
        }

        /* ---------- STATUS BADGES ---------- */
        .status {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 0.80rem;
            font-weight: 700;
            border: 1px solid #dddddd;
        }

        .status-pending {
            background-color: #f0f0f0;
            color: #161616;
        }

        .status-ai {
            background-color: #c5172e;
            color: white;
            border-color: #c5172e;
        }

        .status-processed {
            background-color: #2e7d32;
            color: white;
            border-color: #2e7d32;
        }

        .status-rejected {
            background-color: #8b1e2d;
            color: white;
            border-color: #8b1e2d;
        }

        /* ---------- TABLES ---------- */
        .stDataFrame {
            background-color: white;
            border-radius: 8px;
            border: 1px solid #dddddd;
        }

        /* ---------- INPUTS ---------- */
        input, textarea, select {
            background-color: white !important;
            color: #161616 !important;
        }

        /* ---------- SIDEBAR ---------- */
        section[data-testid="stSidebar"] {
            background-color: #ffffff !important;
            border-right: 1px solid #dddddd;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )

    # Optional top header
    if show_top_header:
        st.markdown(
            f"<h1 style='text-align:center; margin-bottom: 0.25rem;'>{page_title}</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='text-align:center; margin-top:0; color:#666;'>{slogan}</p>",
            unsafe_allow_html=True,
        )
        st.markdown("---")


def render_status(status: str) -> None:
    cls = {
        "PENDING": "status status-pending",
        "AI_PROPOSED": "status status-ai",
        "PROCESSED": "status status-processed",
        "REJECTED": "status status-rejected",
    }.get(status, "status")

    st.markdown(f'<span class="{cls}">{status}</span>', unsafe_allow_html=True)
