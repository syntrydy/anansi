"""Inject design-system CSS/fonts matching the Stitch mockup."""

from __future__ import annotations

import streamlit as st

_FONTS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
"""

_CSS = """
<style>
/* ── Globals ── */
body, .stApp, * { font-family: 'Inter', sans-serif; }
h1, h2, h3, h4 {
    font-family: 'Manrope', sans-serif !important;
    font-weight: 800 !important;
    letter-spacing: -0.025em !important;
}
.stApp { background-color: #faf9f8 !important; color: #1a1c1c !important; }
.main .block-container { padding-top: 3rem !important; max-width: 920px !important; }
#MainMenu, footer, header { visibility: hidden; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background-color: #f4f3f2 !important;
    border-right: 1px solid rgba(224,192,178,0.15);
}

/* ── Form card ── */
[data-testid="stForm"] {
    background-color: #ffffff !important;
    border-radius: 0.75rem !important;
    padding: 2.25rem !important;
    box-shadow: 0 32px 64px -12px rgba(26,28,28,0.07) !important;
    border: none !important;
}

/* ── Field labels ── */
.stTextInput label p, .stSelectbox label p,
.stTextArea label p, .stNumberInput label p,
.stTextInput label, .stSelectbox label,
.stTextArea label, .stNumberInput label {
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    color: #8c7166 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── Text / Number inputs ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    background-color: transparent !important;
    border: none !important;
    border-bottom: 2px solid #e0c0b2 !important;
    border-radius: 0 !important;
    padding: 0.5rem 0 !important;
    font-size: 1rem !important;
    font-weight: 500 !important;
    color: #1a1c1c !important;
    box-shadow: none !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-bottom-color: #9e3d00 !important;
    box-shadow: none !important;
    outline: none !important;
}

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {
    background-color: transparent !important;
    border: none !important;
    border-bottom: 2px solid #e0c0b2 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
}

/* ── TextArea ── */
[data-testid="stTextArea"] textarea {
    background-color: #f4f3f2 !important;
    border: none !important;
    border-radius: 0.75rem !important;
    padding: 1rem !important;
    font-weight: 500 !important;
    color: #594238 !important;
}
[data-testid="stTextArea"] textarea:focus {
    box-shadow: 0 0 0 2px rgba(158,61,0,0.3) !important;
}

/* ── Buttons ── */
.stButton > button,
[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #9e3d00 0%, #c64f00 100%) !important;
    color: #351000 !important;
    font-family: 'Manrope', sans-serif !important;
    font-weight: 800 !important;
    border: none !important;
    border-radius: 0.75rem !important;
    padding: 0.7rem 2rem !important;
    letter-spacing: 0.02em !important;
    box-shadow: 0 4px 14px rgba(158,61,0,0.2) !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover { box-shadow: 0 6px 20px rgba(158,61,0,0.35) !important; }
.stButton > button:active { transform: scale(0.98) !important; }
.stButton > button:disabled { opacity: 0.38 !important; transform: none !important; }

.stFormSubmitButton > button,
[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #9e3d00 0%, #c64f00 100%) !important;
    color: #351000 !important;
    font-family: 'Manrope', sans-serif !important;
    font-weight: 800 !important;
    border: none !important;
    border-radius: 0.75rem !important;
    padding: 0.85rem 2.5rem !important;
    font-size: 1.05rem !important;
    letter-spacing: 0.02em !important;
    width: 100% !important;
    box-shadow: 0 4px 14px rgba(158,61,0,0.2) !important;
}

[data-testid="stDownloadButton"] > button {
    background: linear-gradient(135deg, #9e3d00 0%, #c64f00 100%) !important;
    color: #351000 !important;
    font-family: 'Manrope', sans-serif !important;
    font-weight: 800 !important;
    border: none !important;
    border-radius: 0.75rem !important;
    padding: 1.25rem 2rem !important;
    font-size: 1.15rem !important;
    letter-spacing: 0.02em !important;
    box-shadow: 0 8px 24px rgba(158,61,0,0.25) !important;
    width: 100% !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] { border-radius: 0.75rem !important; border: none !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background-color: #f4f3f2 !important;
    border-radius: 0.75rem !important;
    border: none !important;
}
[data-testid="stExpander"] summary {
    font-family: 'Manrope', sans-serif !important;
    font-weight: 700 !important;
    color: #9e3d00 !important;
    font-size: 1rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}

/* ── Images ── */
[data-testid="stImage"] img { border-radius: 0.75rem !important; }

/* ── Checkbox ── */
[data-testid="stCheckbox"] span p {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
}

/* ── HR ── */
hr { border-color: rgba(224,192,178,0.25) !important; }

/* ── Panel card components ── */
.anansi-panel-card {
    background: #ffffff;
    border-radius: 0.75rem;
    border: 1px solid rgba(224,192,178,0.15);
    box-shadow: 0 4px 16px rgba(26,28,28,0.05);
    margin-bottom: 0.25rem;
    overflow: hidden;
}
.anansi-panel-header {
    padding: 1rem 1.5rem;
    background-color: rgba(244,243,242,0.5);
    border-bottom: 1px solid rgba(224,192,178,0.15);
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.anansi-panel-header h3 {
    font-family: 'Manrope', sans-serif;
    font-weight: 700;
    font-size: 1.05rem;
    margin: 0;
    color: #1a1c1c;
}
.anansi-badge {
    font-size: 0.62rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    padding: 0.2rem 0.65rem;
    border-radius: 9999px;
}
.anansi-badge-active  { color: #9e3d00;  background-color: #ffdbcd; }
.anansi-badge-unsafe  { color: #93000a;  background-color: #ffdad6; }
.anansi-badge-pending { color: rgba(26,28,28,0.4); background-color: #e3e2e1; }

/* ── Pipeline stepper ── */
.anansi-stepper-wrap {
    background-color: #f4f3f2;
    border-radius: 0.75rem;
    padding: 1.5rem 2rem 1.25rem;
    margin-bottom: 0.5rem;
}
.anansi-stepper {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    position: relative;
    padding-top: 0.25rem;
}
.anansi-stepper-track {
    position: absolute;
    top: 1.2rem;
    left: 4%;
    right: 4%;
    height: 4px;
    background-color: rgba(224,192,178,0.35);
    border-radius: 2px;
    z-index: 0;
}
.anansi-stepper-fill {
    position: absolute;
    top: 0;
    left: 0;
    height: 100%;
    background-color: #9e3d00;
    border-radius: 2px;
    transition: width 0.5s ease;
}
.anansi-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    position: relative;
    z-index: 1;
    flex: 1;
}
.anansi-step-circle {
    width: 2.4rem;
    height: 2.4rem;
    border-radius: 9999px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.85rem;
    font-family: 'Manrope', sans-serif;
}
.anansi-step-circle.done    { background-color: #1b6d24; color: #ffffff; }
.anansi-step-circle.active  { background-color: #9e3d00; color: #ffffff;
    animation: stepper-pulse 1.5s ease-in-out infinite; }
.anansi-step-circle.pending { background-color: #e3e2e1; color: rgba(26,28,28,0.4); }
@keyframes stepper-pulse {
    0%   { box-shadow: 0 0 0 0   rgba(158,61,0,0.45); }
    70%  { box-shadow: 0 0 0 10px rgba(158,61,0,0); }
    100% { box-shadow: 0 0 0 0   rgba(158,61,0,0); }
}
.anansi-step-label {
    font-size: 0.62rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-family: 'Inter', sans-serif;
    white-space: nowrap;
}
.anansi-step-label.done    { color: #1b6d24; }
.anansi-step-label.active  { color: #9e3d00; }
.anansi-step-label.pending { color: rgba(26,28,28,0.35); }
.anansi-status-line {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    color: #594238;
    font-size: 0.875rem;
    margin-top: 0.9rem;
    font-weight: 500;
}
.anansi-dot-ping {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #9e3d00;
    animation: dot-ping 1.2s ease-in-out infinite;
    flex-shrink: 0;
}
@keyframes dot-ping {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.4; transform: scale(1.35); }
}
</style>
"""


def inject_styles() -> None:
    """Inject design-system fonts and CSS into the Streamlit page."""
    st.markdown(_FONTS + _CSS, unsafe_allow_html=True)
