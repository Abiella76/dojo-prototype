"""Constants and design tokens shared across the app."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "Dojo"
APP_VERSION = "12.2"

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

CREATE_XP = 10        # accepting a quest — planning is work too
CREATE_REASON = "Quest accepted"   # ledger label; also how the row is protected

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
# The app is dark-only, so there is one palette rather than a pair. Categorical
# slots are in fixed order and never cycled; violet leads because it is the
# product's primary. Validated against the card surface (#0e0e1b): worst
# adjacent CVD ΔE 12.7, worst normal-vision ΔE 24.1, all four clear 3:1.
SERIES = ["#8b7bff", "#22d3ee", "#ff8a1f", "#2dd4a0"]

# Single-hue sequential ramp for the consistency heatmap: one violet hue,
# darkest to brightest, so an empty day recedes into the surface (the first
# step sits at 1.05:1 against it) and a strong day glows. Lightness is
# monotonic in OKLab — 0.203, 0.279, 0.383, 0.504, 0.661, 0.788.
SEQUENTIAL = ["#151033", "#241a5e", "#3a26a0", "#5a3fe0", "#8b7bff", "#b9adff"]


def sequential(_mode: str | None = None) -> list[str]:
    """The heatmap ramp. The argument is vestigial — there is one theme now."""
    return SEQUENTIAL
