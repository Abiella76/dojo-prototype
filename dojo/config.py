"""Constants and design tokens shared across the app."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "Dojo"
APP_VERSION = "11.2"

# ────── storage ──────
# Overridable so tests and deployments can point somewhere writable.
DB_PATH = Path(os.environ.get("DOJO_DB", Path.home() / ".dojo" / "dojo.db"))

# ────── priorities / difficulty tiers ──────
# The stored values never change — they are the keys of the XP table and of
# every row already in the database. TIER_LABELS and TIER_RANKS are display
# only, so the quest framing is skin-deep and old data keeps working.
PRIORITIES = ["Critical", "High", "Medium", "Low"]

TIER_LABELS = {"Critical": "BOSS", "High": "ELITE", "Medium": "STANDARD", "Low": "MINOR"}
TIER_RANKS = {"Critical": "S", "High": "A", "Medium": "B", "Low": "C"}

# Neon tier ramp. Validated as a categorical set against the dark surface
# (#101018): CVD separation, normal-vision separation and 3:1 contrast all
# pass. It deliberately sits above the dark-mode lightness band — being bright
# is the point of the neon skin — and every tier ships its rank letter and
# label beside the colour, so hue is never the only channel.
PRIORITY_COLORS = {
    "Critical": "#ff3d71",
    "High": "#ff8a1f",
    "Medium": "#ffd60a",
    "Low": "#2dd4a0",
}

PRIORITY_GLYPHS = {"Critical": "▲▲", "High": "▲", "Medium": "■", "Low": "▾"}

# ────── experience points ──────
BASE_XP = {"Critical": 50, "High": 30, "Medium": 20, "Low": 10}

EARLY_BONUS = 5       # finished on or before its due date
SWEEP_BONUS = 25      # every task on the board finished
SWEEP_MIN_TASKS = 3   # ...but a one-task day is not a clean sweep

STREAK_TIERS = [(7, 1.5), (3, 1.25)]  # (days, multiplier), checked high to low


def streak_multiplier(streak: int) -> float:
    """Multiplier applied to base XP for a run of consecutive active days."""
    for days, mult in STREAK_TIERS:
        if streak >= days:
            return mult
    return 1.0


# ────── belts ──────
# Cumulative lifetime XP required to hold each belt. The curve widens so early
# ranks arrive quickly and later ones stay meaningful.
# Each colour is the belt's *display* colour on a dark surface, not the literal
# dye — a real black belt rendered #000 is invisible here, so the higher ranks
# use their sheen instead. Every entry clears 4.5:1 against #101018.
BELTS = [
    ("White", 0, "#e8e6e1"),
    ("Yellow", 250, "#ffd60a"),
    ("Orange", 700, "#ff8a1f"),
    ("Green", 1500, "#2dd4a0"),
    ("Blue", 3000, "#22d3ee"),
    ("Purple", 5500, "#a78bfa"),
    ("Brown", 9000, "#c98550"),
    ("Black", 14000, "#b6bcd4"),
    ("Red", 22000, "#ff3d71"),
    ("Grandmaster", 35000, "#ffe14d"),
]


def belt_for_xp(total_xp: int) -> tuple[str, int, str, int | None]:
    """Return (belt name, level, hex colour, XP threshold of the next belt)."""
    held = BELTS[0]
    level = 1
    for i, belt in enumerate(BELTS):
        if total_xp >= belt[1]:
            held, level = belt, i + 1
    nxt = BELTS[level][1] if level < len(BELTS) else None
    return held[0], level, held[2], nxt


def belt_progress(total_xp: int) -> float:
    """Fraction (0-1) of the way from the current belt to the next."""
    _, level, _, nxt = belt_for_xp(total_xp)
    if nxt is None:
        return 1.0
    floor = BELTS[level - 1][1]
    span = nxt - floor
    return max(0.0, min(1.0, (total_xp - floor) / span)) if span else 1.0


# ────── chart palette ──────
# Categorical slots in fixed order (never cycled).
SERIES = {
    "light": ["#0891b2", "#eb6834", "#1baf7a", "#eda100"],
    "dark": ["#22d3ee", "#d95926", "#199e70", "#c98500"],
}

# Single-hue sequential ramp for the consistency heatmap, darkest-to-brightest
# cyan on dark so an empty day recedes into the surface.
SEQUENTIAL_DARK = ["#0e3f4d", "#12657a", "#0e91ad", "#12b5d4", "#22d3ee", "#7ceaf9"]
SEQUENTIAL_LIGHT = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95"]
SEQUENTIAL = SEQUENTIAL_DARK  # back-compat alias


def sequential(mode: str) -> list[str]:
    return SEQUENTIAL_DARK if mode == "dark" else SEQUENTIAL_LIGHT
