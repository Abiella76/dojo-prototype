"""Design tokens and the CSS that restyles Streamlit's own widgets.

The previous version wrapped native widgets in bare `<div>` strings, which
Streamlit renders as separate, immediately-closed nodes — the styling never
reached the widgets. Everything here instead targets Streamlit's real DOM
(`stButton`, `stTextInput`, the bordered vertical block) so it actually lands.
"""

from __future__ import annotations

import streamlit as st

from ..config import PRIORITY_COLORS

TOKENS = {
    "dark": {
        "surface": "#141416",
        "surface_2": "#1c1c1f",
        "surface_3": "#232327",
        "border": "#303036",
        "text": "#f4f4f2",
        "text_2": "#a8a8a2",
        "text_3": "#76766f",
        "accent": "#3987e5",
        "accent_soft": "rgba(57,135,229,0.16)",
        "shadow": "0 1px 2px rgba(0,0,0,.5), 0 8px 24px rgba(0,0,0,.34)",
    },
    "light": {
        "surface": "#fcfcfb",
        "surface_2": "#ffffff",
        "surface_3": "#f2f1ee",
        "border": "#e0dfda",
        "text": "#131311",
        "text_2": "#52514e",
        "text_3": "#84837d",
        "accent": "#2a78d6",
        "accent_soft": "rgba(42,120,214,0.10)",
        "shadow": "0 1px 2px rgba(16,15,14,.06), 0 8px 24px rgba(16,15,14,.07)",
    },
}


def tokens(mode: str) -> dict[str, str]:
    return TOKENS.get(mode, TOKENS["dark"])


def css_vars(mode: str) -> str:
    """The token block, reusable inside component iframes (which have their own DOM)."""
    t = tokens(mode)
    lines = [f"  --{k.replace('_', '-')}: {v};" for k, v in t.items()]
    lines += [f"  --prio-{p.lower()}: {c};" for p, c in PRIORITY_COLORS.items()]
    return "\n".join(lines)


def inject(mode: str) -> None:
    t = tokens(mode)
    priority_rules = "\n".join(
        f'[class*="st-key-card-"]:has(.prio-{p.lower()}) {{ border-left: 3px solid {c} !important; }}'
        for p, c in PRIORITY_COLORS.items()
    )

    st.markdown(
        f"""
<style>
:root {{
{css_vars(mode)}
  --radius: 14px;
}}

/* ── canvas ───────────────────────────────────────────── */
.stApp {{ background: var(--surface); color: var(--text); }}
[data-testid="stHeader"] {{ background: transparent; }}
footer, [data-testid="stDecoration"], [data-testid="stAppDeployButton"],
[data-testid="stStatusWidget"] {{ display: none !important; }}
/* The header is a fixed overlay: let clicks fall through to the tabs beneath it,
   but keep its own controls (sidebar toggle, settings menu) clickable. */
[data-testid="stHeader"] {{ height: 0; pointer-events: none; }}
[data-testid="stHeader"] button, [data-testid="stMainMenu"] {{ pointer-events: auto; }}
.block-container {{ padding: 1.4rem 2rem 5rem; max-width: 1180px; }}
[data-testid="stSidebar"] > div {{
  background: var(--surface-2); border-right: 1px solid var(--border);
}}
.stApp, .stMarkdown, p, span, label, li {{ color: var(--text); }}
h1, h2, h3, h4 {{ color: var(--text); letter-spacing: -0.02em; font-weight: 650; }}
h1 {{ font-size: 1.85rem; }}
hr {{ border-color: var(--border); }}

/* ── cards ──────────────────────────────────────────────
   Streamlit gives a keyed container the class `st-key-<key>`; that is the only
   stable hook it exposes, so every card is keyed and matched on the prefix.
   (The old `stVerticalBlockBorderWrapper` test id no longer exists.) */
[class*="st-key-card-"] {{
  background: var(--surface-2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow);
  transition: box-shadow .18s ease, border-color .18s ease;
}}
[class*="st-key-card-"]:hover {{ border-color: var(--text-3) !important; }}
{priority_rules}
.card-done {{ opacity: .58; }}
.card-done .task-title {{ text-decoration: line-through; text-decoration-thickness: 1px; }}

/* ── task typography ─────────────────────────────────── */
.task-title {{ font-size: 1.02rem; font-weight: 600; line-height: 1.35; margin: 0 0 .35rem; }}
.task-meta {{ display: flex; flex-wrap: wrap; gap: .4rem; align-items: center; margin-bottom: .1rem; }}
.chip {{
  display: inline-flex; align-items: center; gap: .3rem;
  font-size: .69rem; font-weight: 600; letter-spacing: .04em; text-transform: uppercase;
  padding: .2rem .55rem; border-radius: 999px; white-space: nowrap;
  border: 1px solid var(--border); color: var(--text-2); background: var(--surface-3);
}}
.chip-prio {{ color: #fff; border: none; }}
.chip-tag {{ text-transform: none; letter-spacing: 0; font-weight: 500; }}
.chip-due {{ color: var(--text-2); }}
.chip-overdue {{ background: rgba(208,59,59,.14); color: #e06a6a; border-color: rgba(208,59,59,.35); }}
.chip-carried {{ background: transparent; color: var(--text-3); border-style: dashed; }}
.note-body {{
  font-size: .87rem; color: var(--text-2); background: var(--surface-3);
  border-left: 2px solid var(--border); border-radius: 0 8px 8px 0;
  padding: .55rem .75rem; margin: .5rem 0 .1rem; white-space: pre-wrap;
}}
.sub-progress {{ font-size: .75rem; color: var(--text-3); font-variant-numeric: tabular-nums; }}

/* ── buttons ─────────────────────────────────────────── */
.stButton > button, .stDownloadButton > button {{
  border-radius: 999px; border: 1px solid var(--border);
  background: var(--surface-3); color: var(--text);
  font-size: .8rem; font-weight: 550; padding: .3rem .85rem;
  transition: transform .12s ease, background .12s ease, border-color .12s ease;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{
  background: var(--accent-soft); border-color: var(--accent);
  color: var(--text); transform: translateY(-1px);
}}
.stButton > button:active {{ transform: translateY(0); }}
.stButton > button[kind="primary"] {{
  background: var(--accent); border-color: var(--accent); color: #fff;
}}
.stButton > button[kind="primary"]:hover {{ filter: brightness(1.08); color: #fff; }}
.stButton > button:focus-visible, .stTextInput input:focus {{
  outline: 2px solid var(--accent); outline-offset: 1px;
}}

/* ── inputs ──────────────────────────────────────────── */
.stTextInput input, .stTextArea textarea, .stDateInput input, .stSelectbox div[data-baseweb="select"] > div {{
  background: var(--surface-3) !important; border-radius: 10px !important;
  border: 1px solid var(--border) !important; color: var(--text) !important;
}}
.stTextInput input::placeholder {{ color: var(--text-3); }}

/* ── sidebar metrics ─────────────────────────────────── */
[data-testid="stMetricValue"] {{ font-size: 1.35rem; font-weight: 650; color: var(--text); }}
[data-testid="stMetricLabel"] {{ color: var(--text-2); }}
[data-testid="stSidebar"] [data-testid="stMetric"] {{ padding: 0; }}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: .45rem; }}
[data-testid="stSidebar"] hr {{ margin: .55rem 0; }}
[data-testid="stSidebar"] .block-container {{ padding-top: 1.2rem; }}
.prio-critical, .prio-high, .prio-medium, .prio-low {{ display: none; }}

/* ── tabs ────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{ gap: .25rem; border-bottom: 1px solid var(--border); }}
.stTabs [data-baseweb="tab"] {{
  border-radius: 10px 10px 0 0; padding: .5rem 1rem; color: var(--text-2);
}}
.stTabs [aria-selected="true"] {{ color: var(--text); background: var(--surface-3); }}

/* ── motion ──────────────────────────────────────────── */
@keyframes rise {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: none; }} }}
[class*="st-key-card-"] {{ animation: rise .22s ease both; }}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation: none !important; transition: none !important; }}
}}
</style>
""",
        unsafe_allow_html=True,
    )
