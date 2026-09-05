"""Points, belts and achievements — the layer that makes finishing things feel good."""

from __future__ import annotations

import json

from datetime import date
from typing import Any

from . import config, db


def xp_preview(priority: str, streak: int, *, due_date: str | None = None,
               today: date | None = None) -> dict[str, Any]:
    """What completing this task right now would be worth, itemised."""
    today = today or date.today()
    base = config.BASE_XP.get(priority, 20)
    mult = config.streak_multiplier(streak)
    lines = [(f"{priority} task", base)]
    total = int(round(base * mult))
    if mult > 1:
        lines.append((f"{streak}-day streak ×{mult:g}", total - base))
    if due_date:
        try:
            if today <= date.fromisoformat(due_date):
                lines.append(("Ahead of due date", config.EARLY_BONUS))
                total += config.EARLY_BONUS
        except ValueError:
            pass
    return {"total": total, "lines": lines}


def lifetime_stats() -> dict[str, Any]:
    conn = db.connect()
    # One pass per table rather than a query per counter. This runs on every
    # rerun, and against a hosted database each round trip is a network hop —
    # seven of them are plainly felt between clicking Clear and seeing the XP.
    t = conn.execute(
        "SELECT "
        "COALESCE(SUM(CASE WHEN parent_id IS NULL THEN 1 ELSE 0 END), 0) AS created, "
        "COALESCE(SUM(CASE WHEN parent_id IS NULL AND completed = 1 THEN 1 ELSE 0 END), 0) AS done, "
        "COALESCE(SUM(CASE WHEN completed = 1 AND priority = 'Critical' THEN 1 ELSE 0 END), 0) AS crit "
        "FROM tasks"
    ).fetchone()
    x = conn.execute(
        "SELECT "
        "COALESCE(SUM(points), 0) AS total, "
        "COALESCE(SUM(CASE WHEN reason = 'Clean sweep' THEN 1 ELSE 0 END), 0) AS sweeps, "
        "COALESCE(SUM(CASE WHEN reason = 'Ahead of due date' THEN 1 ELSE 0 END), 0) AS early, "
        "COALESCE(SUM(CASE WHEN reason = ? THEN 1 ELSE 0 END), 0) AS accepted "
        "FROM xp_log", (config.CREATE_REASON,)
    ).fetchone()
    # current_streak() derives from active_days(); share the one lookup.
    days = db.active_days()
    total = int(x["total"])
    name, level, colour, nxt = config.belt_for_xp(total)
    return {
        "xp": total, "belt": name, "level": level, "belt_color": colour,
        "next_belt_at": nxt, "progress": config.belt_progress(total),
        "created": int(t["created"]), "done": int(t["done"]),
        "critical_done": int(t["crit"]), "sweeps": int(x["sweeps"]), "early": int(x["early"]),
        "accepted": int(x["accepted"]),
        "streak": db.current_streak(days=days), "active_days": len(days),
    }


# (key, label, description, icon, predicate over lifetime_stats)
#
# Ordered easiest-first within each family so the grid reads as a ladder.
# Accepting quests is counted from the ledger rather than from the task table,
# so restoring a backup or carrying work forward cannot inflate it.
ACHIEVEMENTS = [
    ("first", "First Step", "Clear your first quest", "\u2694\ufe0f", lambda s: s["done"] >= 1),
    ("ten", "Getting Warm", "Clear 10 quests", "\U0001f525", lambda s: s["done"] >= 10),
    ("fifty", "Relentless", "Clear 50 quests", "\u26a1", lambda s: s["done"] >= 50),
    ("century", "Century", "Clear 100 quests", "\U0001f3af", lambda s: s["done"] >= 100),
    ("five_hundred", "Veteran", "Clear 500 quests", "\U0001f396\ufe0f", lambda s: s["done"] >= 500),

    ("boss1", "First Blood", "Clear your first BOSS quest", "\U0001f5e1\ufe0f",
     lambda s: s["critical_done"] >= 1),
    ("boss10", "Boss Hunter", "Clear 10 BOSS quests", "\U0001f480",
     lambda s: s["critical_done"] >= 10),
    ("crisis", "Boss Slayer", "Clear 25 BOSS quests", "\U0001f409",
     lambda s: s["critical_done"] >= 25),
    ("boss100", "Nemesis", "Clear 100 BOSS quests", "\U0001f451",
     lambda s: s["critical_done"] >= 100),

    ("accepted10", "Planner", "Accept 10 quests", "\U0001f4dc", lambda s: s["accepted"] >= 10),
    ("accepted50", "Strategist", "Accept 50 quests", "\U0001f5fa\ufe0f",
     lambda s: s["accepted"] >= 50),
    ("accepted200", "Architect", "Accept 200 quests", "\U0001f3f0",
     lambda s: s["accepted"] >= 200),

    ("streak3", "Momentum", "Hold a 3-day run", "\U0001f3c3", lambda s: s["streak"] >= 3),
    ("streak7", "Week Warrior", "Hold a 7-day run", "\U0001f4c5", lambda s: s["streak"] >= 7),
    ("streak30", "Iron Month", "Hold a 30-day run", "\U0001f9be", lambda s: s["streak"] >= 30),
    ("streak100", "Unbroken", "Hold a 100-day run", "\u267e\ufe0f", lambda s: s["streak"] >= 100),

    ("sweep", "Clean Sweep", "Clear a full day's log", "\U0001f9f9", lambda s: s["sweeps"] >= 1),
    ("sweep10", "Spotless", "Clear the log 10 times", "\u2728", lambda s: s["sweeps"] >= 10),

    ("early5", "Punctual", "Beat 5 due dates", "\u23f1\ufe0f", lambda s: s["early"] >= 5),
    ("early", "Ahead of Time", "Beat 20 due dates", "\U0001f680", lambda s: s["early"] >= 20),

    ("xp1k", "Four Figures", "Bank 1,000 XP", "\U0001f4b0", lambda s: s["xp"] >= 1000),
    ("xp10k", "Five Figures", "Bank 10,000 XP", "\U0001f48e", lambda s: s["xp"] >= 10000),

    ("black", "Black Belt", "Reach rank 8", "\U0001f94b", lambda s: s["level"] >= 8),
    ("grandmaster", "Grandmaster", "Reach rank 10", "\U0001f3c6", lambda s: s["level"] >= 10),
]

SEEN_SETTING = "achievements_seen"


def achievements(stats: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    stats = stats or lifetime_stats()
    return [
        {"key": key, "label": label, "description": desc, "icon": icon,
         "earned": bool(test(stats))}
        for key, label, desc, icon, test in ACHIEVEMENTS
    ]


def claim_new_achievements(stats: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Achievements earned since the last check, recorded so they fire once.

    The first call ever seeds the record silently. An established board has
    already met a dozen of these, and erupting in a dozen badges the first time
    the feature ships would be noise, not celebration — they were not earned
    just now.
    """
    stats = stats or lifetime_stats()
    earned = [a for a in achievements(stats) if a["earned"]]
    keys = {a["key"] for a in earned}

    raw = db.get_setting(SEEN_SETTING)
    if raw is None:
        db.set_setting(SEEN_SETTING, json.dumps(sorted(keys)))
        return []
    try:
        seen = set(json.loads(raw))
    except (TypeError, ValueError):
        seen = set()

    fresh = [a for a in earned if a["key"] not in seen]
    if fresh:
        db.set_setting(SEEN_SETTING, json.dumps(sorted(seen | keys)))
    return fresh


def rank_message(stats: dict[str, Any]) -> str:
    if stats["next_belt_at"] is None:
        return "Grandmaster. Nothing left to climb."
    remaining = stats["next_belt_at"] - stats["xp"]
    nxt = config.BELTS[stats["level"]][0]
    return f"{remaining:,} XP to {nxt} belt"
