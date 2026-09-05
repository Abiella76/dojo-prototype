"""Design tokens and the CSS that restyles Streamlit's own widgets.

The skin is a dark, techy console theme: near-black navy ground under a faint
blueprint grid, a violet primary with a cyan counterpart. Everything targets Streamlit's real DOM
(`stButton`, `stTextInput`, keyed containers) rather than bare `<div>` wrappers,
which Streamlit renders as separate nodes that never reach the widgets.

Colour rules the palette is held to:
  * Difficulty tiers keep their validated ramp and always ship a rank letter
    and label, so hue is never the only channel carrying meaning.
  * Every text token clears 4.5:1 against the surface it sits on.
"""

from __future__ import annotations

import streamlit as st

from ..config import PRIORITY_COLORS

# One palette: the app is dark-only. A techy console look — near-black navy
# ground, a violet primary with a cyan counterpart, and gradients that run
# violet → blue → cyan.
#
# Every value here is measured, not picked by eye:
#   text 16.8:1, text-2 8.1:1, text-3 5.2:1 on the card surface
#   accent (as text) 5.8:1 — a dimmer violet reads prettier but lands at 4.4:1
#   white on both button-gradient stops: 6.5:1 and 5.2:1
TOKENS = {
    "dark": {
        "surface": "#070710",
        "surface_2": "#0e0e1b",
        "surface_3": "#16162b",
        "border": "#23233d",
        "border_lit": "#3a3a63",
        "text": "#eef0f8",
        "text_2": "#a2a8c4",
        "text_3": "#7b83a8",
        "accent": "#8b7bff",
        "accent_2": "#22d3ee",
        # The button fill is a step darker than the accent so white type on it
        # clears 4.5:1. The prettier violet does not, which is worth knowing:
        # plenty of decks ship that exact combination failing.
        "accent_btn": "#6d4aff",
        "accent_btn_2": "#5730d8",
        "accent_soft": "rgba(124,92,255,0.16)",
        "glow": "rgba(124,92,255,0.45)",
        "glow_2": "rgba(34,211,238,0.35)",
        "shadow": "0 2px 0 #04040a, 0 12px 34px rgba(0,0,0,.65)",
    },
}

# No webfont. A render-blocking @import is a single point of failure for the
# whole page — if the font host is slow or blocked the app paints nothing until
# it times out. System stacks are instant and always available; the arcade feel
# comes from weight, tracking and caps instead.
DISPLAY_STACK = ("ui-monospace, 'SF Mono', 'Cascadia Mono', 'Roboto Mono', "
                 "'Segoe UI Mono', Consolas, monospace")
UI_STACK = ("'Source Sans Pro', -apple-system, BlinkMacSystemFont, 'Segoe UI', "
            "system-ui, sans-serif")


def tokens(mode: str) -> dict[str, str]:
    return TOKENS.get(mode, TOKENS["dark"])


def css_vars(mode: str) -> str:
    """The token block, reusable inside component iframes (own document)."""
    t = tokens(mode)
    lines = [f"  --{k.replace('_', '-')}: {v};" for k, v in t.items()]
    lines += [f"  --tier-{p.lower()}: {c};" for p, c in PRIORITY_COLORS.items()]
    lines.append(f"  --font-display: {DISPLAY_STACK};")
    lines.append(f"  --font-ui: {UI_STACK};")
    return "\n".join(lines)


def inject(mode: str) -> None:
    t = tokens(mode)

    tier_rules = "\n".join(
        f'[class*="st-key-card-"]:has(.tier-{p.lower()}) {{'
        f" border-left: 3px solid {c} !important;"
        f" box-shadow: -8px 0 22px -14px {c}, {t['shadow']}; }}"
        for p, c in PRIORITY_COLORS.items()
    )

    # The techy ground: a faint blueprint grid that fades out down the page,
    # plus two soft glows — violet at the top left, cyan opposite — so the
    # background has depth instead of being flat black.
    canvas = """
.stApp::before {
  content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background-image:
    linear-gradient(rgba(139,123,255,.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(139,123,255,.055) 1px, transparent 1px);
  background-size: 64px 64px;
  -webkit-mask-image: radial-gradient(130% 95% at 50% 0%, #000 28%, transparent 76%);
  mask-image: radial-gradient(130% 95% at 50% 0%, #000 28%, transparent 76%);
}
.stApp::after {
  content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background:
    radial-gradient(58% 44% at 10% 0%, rgba(124,92,255,.22), transparent 68%),
    radial-gradient(52% 38% at 92% 4%, rgba(34,211,238,.10), transparent 70%);
}
"""

    st.markdown(
        f"""
<style>
:root {{
{css_vars(mode)}
  --radius: 12px;
}}

/* ── canvas ───────────────────────────────────────────── */
.stApp {{ background: var(--surface); color: var(--text); }}
[data-testid="stHeader"] {{ background: transparent; }}
footer, [data-testid="stDecoration"], [data-testid="stAppDeployButton"],
[data-testid="stStatusWidget"] {{ display: none !important; }}
/* The header and its toolbar are fixed overlays that sit on top of the tab
   strip and swallow its clicks. Make the chrome click-through and re-enable
   only its real controls, then keep enough top padding that the tabs clear the
   header band entirely. */
[data-testid="stHeader"], [data-testid="stToolbar"] {{ pointer-events: none !important; }}
[data-testid="stHeader"] {{ height: 0; }}
[data-testid="stHeader"] button, [data-testid="stToolbar"] button,
[data-testid="stMainMenu"], [data-testid="stToolbar"] [role="button"] {{
  pointer-events: auto !important;
}}
.block-container {{ padding: 2.6rem 2rem 5rem; max-width: 1180px; position: relative; z-index: 1; }}
[data-testid="stSidebar"] > div {{
  background: var(--surface-2); border-right: 1px solid var(--border);
}}
[data-testid="stSidebar"] * {{ position: relative; z-index: 1; }}
{canvas}

html, body, .stApp, .stMarkdown, p, span, label, li, input, textarea, button {{
  font-family: var(--font-ui);
}}
.stApp, .stMarkdown, p, span, label, li {{ color: var(--text); }}
h1, h2, h3, h4 {{
  color: var(--text); font-family: var(--font-ui);
  letter-spacing: .01em; font-weight: 700;
}}
h1 {{ font-size: 1.7rem; }}
h3 {{ font-size: 1.15rem; text-transform: uppercase; letter-spacing: .08em; }}
hr {{ border-color: var(--border); }}
code {{ font-family: ui-monospace, 'SF Mono', monospace; color: var(--accent); }}

/* ── quest cards ────────────────────────────────────────
   Streamlit gives a keyed container the class `st-key-<key>`; that is the only
   stable hook it exposes, so every card is keyed and matched on the prefix. */
[class*="st-key-card-"] {{
  background: linear-gradient(180deg, var(--surface-2), var(--surface)) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  box-shadow: {t['shadow']};
  transition: border-color .18s ease, transform .18s ease;
}}
[class*="st-key-card-"]:hover {{
  border-color: var(--border-lit) !important; transform: translateY(-1px);
}}
{tier_rules}
.card-done {{ opacity: .5; }}
.card-done .quest-title {{ text-decoration: line-through; text-decoration-thickness: 1px; }}

/* ── quest typography ───────────────────────────────────── */
.quest-title {{ font-size: 1.02rem; font-weight: 600; line-height: 1.35; margin: .1rem 0 .4rem; }}
.quest-meta {{ display: flex; flex-wrap: wrap; gap: .35rem; align-items: center; }}
.chip {{
  display: inline-flex; align-items: center; gap: .3rem;
  font-size: .66rem; font-weight: 700; letter-spacing: .09em; text-transform: uppercase;
  padding: .2rem .5rem; border-radius: 4px; white-space: nowrap;
  border: 1px solid var(--border); color: var(--text-2); background: var(--surface-3);
}}
.chip-tier {{
  color: #070710; border: none; font-weight: 800;
  clip-path: polygon(6px 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%, 0 6px);
}}
.chip-rank {{
  display: inline-grid; place-items: center; width: 15px; height: 15px;
  border-radius: 3px; background: rgba(0,0,0,.28); font-size: .6rem;
}}
.chip-tag {{ text-transform: none; letter-spacing: .02em; font-weight: 600; }}
.chip-overdue {{
  background: rgba(255,61,113,.14); color: #ff6b93;
  border-color: rgba(255,61,113,.45); animation: pulse 1.8s ease-in-out infinite;
}}
@keyframes pulse {{ 50% {{ opacity: .55; }} }}
.chip-carried {{ background: transparent; color: var(--text-3); border-style: dashed; }}
.note-body {{
  font-size: .87rem; color: var(--text-2); background: var(--surface-3);
  border-left: 2px solid var(--accent); border-radius: 0 6px 6px 0;
  padding: .55rem .75rem; margin: .5rem 0 .1rem; white-space: pre-wrap;
}}
.reward {{
  font-family: var(--font-display); font-size: .74rem; font-weight: 600;
  color: var(--accent); letter-spacing: .04em; white-space: nowrap;
}}
.objectives {{ font-size: .72rem; color: var(--text-3); font-variant-numeric: tabular-nums;
               letter-spacing: .05em; text-transform: uppercase; font-weight: 600; }}

/* ── arcade buttons: pressable, with a hard bottom edge ── */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
  border-radius: 8px;
  border: 1px solid var(--border-lit);
  background: var(--surface-3); color: var(--text);
  font-family: var(--font-ui); font-size: .78rem; font-weight: 700;
  letter-spacing: .07em; text-transform: uppercase;
  padding: .34rem .9rem;
  box-shadow: 0 3px 0 var(--border), 0 4px 10px rgba(0,0,0,.35);
  transition: transform .07s ease, box-shadow .07s ease,
              background .15s ease, border-color .15s ease;
}}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {{
  background: var(--accent-soft); border-color: var(--accent); color: var(--text);
  transform: translateY(-1px);
  box-shadow: 0 4px 0 var(--border), 0 8px 18px rgba(0,0,0,.45), 0 0 16px var(--glow);
}}
/* the press: button drops onto its own shadow */
.stButton > button:active, .stDownloadButton > button:active,
.stFormSubmitButton > button:active {{
  transform: translateY(3px);
  box-shadow: 0 0 0 var(--border), 0 1px 4px rgba(0,0,0,.4), 0 0 10px var(--glow);
}}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
  background: linear-gradient(180deg, var(--accent-btn), var(--accent-btn-2));
  border-color: var(--accent-btn); color: #ffffff;
  box-shadow: 0 3px 0 rgba(0,0,0,.45), 0 8px 22px rgba(0,0,0,.5),
              0 0 24px var(--glow);
}}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover {{
  filter: brightness(1.1); color: #ffffff;
  box-shadow: 0 4px 0 rgba(0,0,0,.45), 0 10px 28px rgba(0,0,0,.55),
              0 0 40px var(--glow);
}}
.stButton > button:focus-visible, .stFormSubmitButton > button:focus-visible {{
  outline: 2px solid var(--accent-2); outline-offset: 2px;
}}

/* ── inputs ─────────────────────────────────────────────── */
.stTextInput input, .stTextArea textarea, .stDateInput input,
.stSelectbox div[data-baseweb="select"] > div {{
  background: var(--surface-3) !important; border-radius: 8px !important;
  border: 1px solid var(--border) !important; color: var(--text) !important;
}}
.stTextInput input:focus, .stTextArea textarea:focus {{
  border-color: var(--accent) !important; box-shadow: 0 0 0 2px var(--accent-soft) !important;
}}
.stTextInput input::placeholder {{ color: var(--text-3); }}

/* ── sidebar readouts ───────────────────────────────────── */
[data-testid="stMetricValue"] {{
  font-family: var(--font-display); font-size: 1.3rem; font-weight: 800;
  color: var(--text); letter-spacing: .02em;
}}
[data-testid="stMetricLabel"] {{
  color: var(--text-3); text-transform: uppercase; letter-spacing: .1em; font-size: .7rem;
}}
[data-testid="stSidebar"] [data-testid="stMetric"] {{ padding: 0; }}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: .4rem; }}
[data-testid="stSidebar"] hr {{ margin: .5rem 0; }}
.tier-critical, .tier-high, .tier-medium, .tier-low {{ display: none; }}

/* ── tabs ───────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{ gap: .3rem; border-bottom: 1px solid var(--border); }}
.stTabs [data-baseweb="tab"] {{
  border-radius: 6px 6px 0 0; padding: .45rem 1.1rem; color: var(--text-3);
  text-transform: uppercase; letter-spacing: .1em; font-size: .78rem; font-weight: 700;
}}
.stTabs [aria-selected="true"] {{
  color: var(--text); background: var(--surface-3);
  box-shadow: inset 0 -2px 0 var(--accent);
}}
/* Section headings read as console labels: cyan, monospaced, wide tracking,
   with a rule leading into them. */
h3 {{
  color: var(--accent-2) !important; font-family: var(--font-display) !important;
  font-size: .82rem !important; letter-spacing: .22em !important;
  display: flex; align-items: center; gap: .6rem;
}}
h3::before {{
  content: ""; width: 26px; height: 1px; background: var(--accent-2); flex: none;
}}

/* ── reward burst ───────────────────────────────────────
   A full-screen, pointer-events-none overlay so it can't block a click. It
   sits centre-screen rather than up by the HUD: an iframe always paints above
   the parent's positioned content, so anything overlapping the HUD panel would
   be hidden behind it no matter its z-index. */
.burst-layer {{
  position: fixed; inset: 0; z-index: 2147483000; pointer-events: none;
  display: grid; place-items: center;
}}
.burst-flash {{
  position: absolute; width: 60vmin; height: 60vmin; border-radius: 50%;
  background: radial-gradient(circle, var(--glow) 0%, transparent 62%);
  animation: flash .55s ease-out forwards;
}}
@keyframes flash {{
  0% {{ opacity: 0; transform: scale(.2); }}
  22% {{ opacity: .85; }}
  100% {{ opacity: 0; transform: scale(1.5); }}
}}
.burst-num {{
  position: relative; text-align: center;
  font-family: var(--font-display); font-weight: 800; letter-spacing: .02em;
  font-size: clamp(3rem, 11vmin, 7rem); line-height: 1;
  color: var(--accent);
  text-shadow: 0 0 18px var(--glow), 0 0 55px var(--glow), 0 4px 0 rgba(0,0,0,.5);
  animation: burstpop 1.9s cubic-bezier(.16,.9,.3,1) forwards;
}}
.burst-num small {{
  display: block; margin-top: .5rem;
  font-size: clamp(.6rem, 1.7vmin, .9rem); letter-spacing: .42em;
  color: var(--accent-2); text-shadow: 0 0 12px var(--accent-2);
}}
@keyframes burstpop {{
  0%   {{ opacity: 0; transform: translateY(26px) scale(.35) rotate(-6deg); }}
  16%  {{ opacity: 1; transform: translateY(0) scale(1.25) rotate(2deg); }}
  28%  {{ transform: translateY(0) scale(1) rotate(0); }}
  62%  {{ opacity: 1; transform: translateY(-26px) scale(1); }}
  100% {{ opacity: 0; transform: translateY(-160px) scale(.92); }}
}}
/* sparks thrown outward on the impact frame */
.spark {{
  position: absolute; width: 9px; height: 9px; border-radius: 50%;
  background: var(--accent); box-shadow: 0 0 12px var(--accent);
  animation: fly 1.1s cubic-bezier(.15,.85,.3,1) forwards;
}}
.spark:nth-child(even) {{ background: var(--accent-2); box-shadow: 0 0 12px var(--accent-2); }}
@keyframes fly {{
  0%   {{ opacity: 0; transform: rotate(var(--a)) translateX(0) scale(.4); }}
  18%  {{ opacity: 1; }}
  100% {{ opacity: 0; transform: rotate(var(--a)) translateX(var(--d)) scale(.2); }}
}}
/* the audio element is only a carrier for autoplay — never show the player.
   Clipped rather than display:none, which some browsers treat as "not playing". */
[class*="st-key-sfx-"] {{
  position: absolute !important; width: 1px !important; height: 1px !important;
  overflow: hidden !important; clip: rect(0 0 0 0); white-space: nowrap;
  border: 0 !important; padding: 0 !important; margin: -1px !important;
  box-shadow: none !important; background: transparent !important;
}}

/* ── rank-up dialog ────────────────────────────────────── */
[data-testid="stDialog"] div[role="dialog"] {{
  background: linear-gradient(180deg, var(--surface-2), var(--surface));
  border: 1px solid var(--accent); border-radius: 14px;
  box-shadow: 0 0 60px var(--glow), 0 24px 60px rgba(0,0,0,.7);
}}
[data-testid="stDialog"] h2 {{
  font-family: var(--font-display); letter-spacing: .3em; font-size: 1rem;
  color: var(--accent); text-align: center;
}}

/* ── motion ─────────────────────────────────────────────── */
@keyframes rise {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: none; }} }}
[class*="st-key-card-"] {{ animation: rise .22s ease both; }}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation: none !important; transition: none !important; }}
  /* The server-drawn burst has no removal timer of its own: with its animation
     gone it would render at its static styles and sit on screen indefinitely,
     so that one stays hidden. */
  .burst-layer {{ display: none !important; }}
  /* The click-time burst *is* removed on a timer, so it can still show the
     points. Reducing motion means dropping the motion — the sparks and the
     flash — not withholding the feedback itself. */
  .burst-layer.burst-still {{ display: grid !important; }}
  .burst-layer.burst-still .spark,
  .burst-layer.burst-still .burst-flash {{ display: none !important; }}
  /* The animated burst travels and fades, so overlapping the page barely
     registers. A still one just sits there, so give it a card to sit on. */
  .burst-layer.burst-still .burst-num {{
    padding: .55rem 1.6rem 1rem; border-radius: 18px;
    background: var(--surface-2); border: 1px solid var(--accent);
    box-shadow: 0 10px 40px rgba(0,0,0,.35);
  }}
}}
</style>
""",
        unsafe_allow_html=True,
    )
