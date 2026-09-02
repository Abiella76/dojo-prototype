"""Constants and design tokens shared across the app."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "Dojo"
APP_VERSION = "11.0"

# ────── storage ──────
# Overridable so tests and deployments can point somewhere writable.
DB_PATH = Path(os.environ.get("DOJO_DB", Path.home() / ".dojo" / "dojo.db"))

# ────── priorities ──────
# Ordinal severity, highest first. Colours come from the reserved *status*
# palette (never the categorical slots) so a priority can never impersonate a
# data series. Every badge ships the label alongside the colour, so meaning is
# never carried by hue alone.
PRIORITIES = ["Critical", "High", "Medium", "Low"]

PRIORITY_COLORS = {
    "Critical": "#d03b3b",  # status: critical
    "High": "#ec835a",      # status: serious
    "Medium": "#fab219",    # status: warning
    "Low": "#0ca30c",       # status: good
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
BELTS = [
    ("White", 0, "#e8e6e1"),
    ("Yellow", 250, "#fab219"),
    ("Orange", 700, "#ec835a"),
    ("Green", 1500, "#0ca30c"),
    ("Blue", 3000, "#2a78d6"),
    ("Purple", 5500, "#4a3aa7"),
    ("Brown", 9000, "#7a4a24"),
    ("Black", 14000, "#26262b"),
    ("Red", 22000, "#d03b3b"),
    ("Grandmaster", 35000, "#eda100"),
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
# Categorical slots in fixed order (never cycled) from the validated default.
SERIES = {
    "light": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"],
    "dark": ["#3987e5", "#d95926", "#199e70", "#c98500"],
}

# Single-hue sequential ramp (blue), lightest -> darkest, for the heatmap.
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95"]
