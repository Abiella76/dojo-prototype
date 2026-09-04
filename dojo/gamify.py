"""Points, belts and achievements — the layer that makes finishing things feel good."""

from __future__ import annotations

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
        "COALESCE(SUM(CASE WHEN reason = 'Ahead of due date' THEN 1 ELSE 0 END), 0) AS early "
        "FROM xp_log"
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
        "streak": db.current_streak(days=days), "active_days": len(days),
    }


# (key, label, description, predicate over lifetime_stats)
ACHIEVEMENTS = [
    ("first", "First Step", "Clear your first quest", lambda s: s["done"] >= 1),
    ("ten", "Getting Warm", "Clear 10 quests", lambda s: s["done"] >= 10),
    ("century", "Century", "Clear 100 quests", lambda s: s["done"] >= 100),
    ("five_hundred", "Veteran", "Clear 500 quests", lambda s: s["done"] >= 500),
    ("streak3", "Momentum", "Hold a 3-day run", lambda s: s["streak"] >= 3),
    ("streak7", "Week Warrior", "Hold a 7-day run", lambda s: s["streak"] >= 7),
    ("streak30", "Iron Month", "Hold a 30-day run", lambda s: s["streak"] >= 30),
    ("sweep", "Clean Sweep", "Clear a full day's log", lambda s: s["sweeps"] >= 1),
    ("sweep10", "Spotless", "Clear the log 10 times", lambda s: s["sweeps"] >= 10),
    ("crisis", "Boss Slayer", "Clear 25 BOSS quests", lambda s: s["critical_done"] >= 25),
    ("early", "Ahead of Time", "Beat 20 due dates", lambda s: s["early"] >= 20),
    ("black", "Black Belt", "Reach rank 8", lambda s: s["level"] >= 8),
]


def achievements(stats: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    stats = stats or lifetime_stats()
    return [
        {"key": key, "label": label, "description": desc, "earned": bool(test(stats))}
        for key, label, desc, test in ACHIEVEMENTS
    ]


def rank_message(stats: dict[str, Any]) -> str:
    if stats["next_belt_at"] is None:
        return "Grandmaster. Nothing left to climb."
    remaining = stats["next_belt_at"] - stats["xp"]
    nxt = config.BELTS[stats["level"]][0]
    return f"{remaining:,} XP to {nxt} belt"
