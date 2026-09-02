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
    row = conn.execute(
        "SELECT COUNT(*) AS created, COALESCE(SUM(completed), 0) AS done "
        "FROM tasks WHERE parent_id IS NULL"
    ).fetchone()
    crit = conn.execute(
        "SELECT COUNT(*) AS n FROM tasks WHERE completed = 1 AND priority = 'Critical'"
    ).fetchone()["n"]
    sweeps = conn.execute(
        "SELECT COUNT(*) AS n FROM xp_log WHERE reason = 'Clean sweep'"
    ).fetchone()["n"]
    early = conn.execute(
        "SELECT COUNT(*) AS n FROM xp_log WHERE reason = 'Ahead of due date'"
    ).fetchone()["n"]
    total = db.total_xp()
    name, level, colour, nxt = config.belt_for_xp(total)
    return {
        "xp": total, "belt": name, "level": level, "belt_color": colour,
        "next_belt_at": nxt, "progress": config.belt_progress(total),
        "created": int(row["created"]), "done": int(row["done"]),
        "critical_done": int(crit), "sweeps": int(sweeps), "early": int(early),
        "streak": db.current_streak(), "active_days": len(db.active_days()),
    }


# (key, label, description, predicate over lifetime_stats)
ACHIEVEMENTS = [
    ("first", "First Step", "Finish your first task", lambda s: s["done"] >= 1),
    ("ten", "Getting Warm", "Finish 10 tasks", lambda s: s["done"] >= 10),
    ("century", "Century", "Finish 100 tasks", lambda s: s["done"] >= 100),
    ("five_hundred", "Veteran", "Finish 500 tasks", lambda s: s["done"] >= 500),
    ("streak3", "Momentum", "Hold a 3-day streak", lambda s: s["streak"] >= 3),
    ("streak7", "Week Warrior", "Hold a 7-day streak", lambda s: s["streak"] >= 7),
    ("streak30", "Iron Month", "Hold a 30-day streak", lambda s: s["streak"] >= 30),
    ("sweep", "Clean Sweep", "Clear a full day's board", lambda s: s["sweeps"] >= 1),
    ("sweep10", "Spotless", "Clear the board 10 times", lambda s: s["sweeps"] >= 10),
    ("crisis", "Crisis Manager", "Finish 25 Critical tasks", lambda s: s["critical_done"] >= 25),
    ("early", "Ahead of Time", "Beat 20 due dates", lambda s: s["early"] >= 20),
    ("black", "Black Belt", "Reach the Black belt", lambda s: s["level"] >= 8),
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
