"""Persistence for Dojo — SQLite by default, Postgres when one is configured.

Everything the app knows lives here, so state survives a browser refresh, a
restart, or a redeploy. The module deliberately has no hard Streamlit import:
it is plain Python and is unit-testable on its own.

Backend selection is by connection URL (see `resolve_url`). With no URL it
falls back to a local SQLite file, which is right for laptops and for tests.
Point DATABASE_URL at Neon (or any Postgres) and the same schema and the same
queries run there instead — necessary on Streamlit Community Cloud, whose disk
is wiped whenever the app sleeps or redeploys.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from . import config

_local = threading.local()

_PG_PREFIXES = ("postgres://", "postgresql://", "postgresql+psycopg://", "postgresql+psycopg2://")

# Shared table definitions. Only the id column differs between the two engines,
# so it is substituted rather than duplicating the whole schema.
_TABLES = """
CREATE TABLE IF NOT EXISTS tasks (
    id           {pk},
    parent_id    INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
    day          TEXT    NOT NULL,
    text         TEXT    NOT NULL,
    notes        TEXT    NOT NULL DEFAULT '',
    priority     TEXT    NOT NULL DEFAULT 'Medium',
    completed    INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT,
    due_date     TEXT,
    tags         TEXT    NOT NULL DEFAULT '[]',
    sort_order   INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT    NOT NULL,
    carried_from TEXT
);
CREATE INDEX IF NOT EXISTS idx_tasks_day    ON tasks(day);
CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_id);

CREATE TABLE IF NOT EXISTS xp_log (
    id         {pk},
    day        TEXT    NOT NULL,
    task_id    INTEGER,
    points     INTEGER NOT NULL,
    reason     TEXT    NOT NULL,
    created_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_xp_day ON xp_log(day);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

SCHEMA = _TABLES.format(pk="INTEGER PRIMARY KEY AUTOINCREMENT")  # sqlite, kept for reference


def resolve_url(explicit: str | None = None) -> str | None:
    """Find a Postgres URL, or None to use SQLite.

    Accepts every convention in common use so it drops into an existing
    Streamlit project without rewiring secrets:
      * DATABASE_URL / NEON_DATABASE_URL in the environment
      * DATABASE_URL at the top level of st.secrets
      * [connections.postgresql] url  — what st.connection("postgresql") uses
      * [postgres] url
    """
    if explicit:
        return explicit
    for var in ("DATABASE_URL", "NEON_DATABASE_URL"):
        if os.environ.get(var, "").strip():
            return os.environ[var].strip()
    try:  # Streamlit is optional — tests and scripts run without it.
        import streamlit as st

        secrets = st.secrets
        for key in ("DATABASE_URL", "NEON_DATABASE_URL"):
            if key in secrets and str(secrets[key]).strip():
                return str(secrets[key]).strip()
        for section in ("connections", "postgres", "neon"):
            if section not in secrets:
                continue
            block = secrets[section]
            block = block.get("postgresql", block) if section == "connections" else block
            for key in ("url", "URL", "dsn", "DATABASE_URL"):
                if key in block and str(block[key]).strip():
                    return str(block[key]).strip()
    except Exception:
        pass
    return None


def _is_pg(url: str | None) -> bool:
    return bool(url) and url.startswith(_PG_PREFIXES)


class StorageError(RuntimeError):
    """A configured database could not be reached. Carries no credentials."""


def safe_target(url: str | None) -> str:
    """Describe a URL as host/database, with any credentials stripped.

    Safe to print in the UI or logs — a connection string carries a password.
    """
    if not url:
        return "(none)"
    try:
        from urllib.parse import urlsplit

        parts = urlsplit(url)
        host = parts.hostname or "(no host)"
        port = f":{parts.port}" if parts.port else ""
        name = (parts.path or "").lstrip("/") or "(no database)"
        return f"{host}{port}/{name}"
    except Exception:
        return "(unparseable URL)"


class _DB:
    """Thin adapter so one set of SQL statements runs on either engine."""

    def __init__(self, raw: Any, is_pg: bool) -> None:
        self.raw = raw
        self.is_pg = is_pg

    def _translate(self, sql: str) -> str:
        if not self.is_pg:
            return sql
        # SQLite's `IS ?` doubles as a null-safe equality test; Postgres spells
        # that IS NOT DISTINCT FROM. Do this before the placeholder swap.
        sql = sql.replace("IS ?", "IS NOT DISTINCT FROM ?")
        return sql.replace("?", "%s")

    def execute(self, sql: str, params: Any = ()) -> Any:
        return self.raw.execute(self._translate(sql), tuple(params))

    def insert(self, sql: str, params: Any = ()) -> int:
        """Run an INSERT and return the new row id, on either engine."""
        if self.is_pg:
            cur = self.raw.execute(self._translate(sql) + " RETURNING id", tuple(params))
            return int(cur.fetchone()["id"])
        return int(self.raw.execute(sql, tuple(params)).lastrowid)

    def commit(self) -> None:
        self.raw.commit()

    def close(self) -> None:
        try:
            self.raw.close()
        except Exception:
            pass

    def alive(self) -> bool:
        try:
            self.raw.execute("SELECT 1")
            return True
        except Exception:
            return False

    def resync_sequences(self) -> None:
        """After inserting explicit ids, move the identity sequences past them.

        Only Postgres needs this: SQLite's AUTOINCREMENT already tracks the max.
        Without it the next insert would collide with a restored row.
        """
        if not self.is_pg:
            return
        for table in ("tasks", "xp_log"):
            self.raw.execute(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                f"COALESCE((SELECT MAX(id) FROM {table}), 1))"
            )
        self.commit()


def _open(url: str | None, path: Path | str | None) -> _DB:
    if _is_pg(url):
        import psycopg
        from psycopg.rows import dict_row

        try:
            raw = psycopg.connect(url, autocommit=False, row_factory=dict_row)
        except Exception as exc:
            # Never surface the original text: psycopg echoes the connection
            # string, password included, in some failure modes.
            raise StorageError(
                f"Could not reach the Postgres database at {safe_target(url)} "
                f"({type(exc).__name__})."
            ) from None
        db = _DB(raw, True)
        for statement in _TABLES.format(pk="SERIAL PRIMARY KEY").split(";"):
            if statement.strip():
                raw.execute(statement)
        db.commit()
        return db

    target = Path(path or config.DB_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = sqlite3.connect(target, check_same_thread=False)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys = ON")
    raw.executescript(_TABLES.format(pk="INTEGER PRIMARY KEY AUTOINCREMENT"))
    raw.commit()
    return _DB(raw, False)


def connect(path: Path | str | None = None, url: str | None = None) -> _DB:
    """Thread-local connection. Streamlit reruns can land on any worker thread.

    A managed Postgres such as Neon drops idle connections, so a cached handle
    is pinged and transparently reopened rather than surfacing as an error the
    first time the app is used after a quiet spell.
    """
    resolved = resolve_url(url)
    key = resolved or str(Path(path or config.DB_PATH))

    existing = getattr(_local, "conn", None)
    if existing is not None and getattr(_local, "key", None) == key:
        if existing.alive():
            return existing
        existing.close()  # stale — fall through and reopen
    elif existing is not None:
        existing.close()

    db = _open(resolved, path)
    _local.conn, _local.key = db, key
    return db


def backend() -> str:
    """'postgres' or 'sqlite' — for the sidebar readout."""
    return "postgres" if connect().is_pg else "sqlite"


def reset_connection() -> None:
    """Drop the cached handle — used by tests switching databases."""
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
    _local.conn = None
    _local.key = None


# ────── settings ──────

def get_setting(key: str, default: str | None = None) -> str | None:
    row = connect().execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    conn = connect()
    conn.execute(
        "INSERT INTO settings(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()


# ────── tasks ──────

def _row_to_task(row: sqlite3.Row) -> dict[str, Any]:
    task = dict(row)
    task["completed"] = bool(task["completed"])
    try:
        task["tags"] = json.loads(task["tags"]) or []
    except (json.JSONDecodeError, TypeError):
        task["tags"] = []
    return task


def add_task(
    day: str,
    text: str,
    priority: str = "Medium",
    *,
    notes: str = "",
    due_date: str | None = None,
    tags: Iterable[str] | None = None,
    parent_id: int | None = None,
    carried_from: str | None = None,
) -> int:
    text = text.strip()
    if not text:
        raise ValueError("task text cannot be empty")
    if priority not in config.PRIORITY_COLORS:
        priority = "Medium"
    conn = connect()
    nxt = conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM tasks WHERE day = ? AND parent_id IS ?",
        (day, parent_id),
    ).fetchone()["n"]
    task_id = conn.insert(
        "INSERT INTO tasks(parent_id, day, text, notes, priority, due_date, tags, "
        "sort_order, created_at, carried_from) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            parent_id, day, text, notes, priority, due_date,
            json.dumps(sorted({t.strip().lower() for t in (tags or []) if t.strip()})),
            nxt, datetime.now().isoformat(timespec="seconds"), carried_from,
        ),
    )
    conn.commit()
    _sync_sweep_bonus(day)
    return task_id


def get_task(task_id: int) -> dict[str, Any] | None:
    row = connect().execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _row_to_task(row) if row else None


def list_tasks(day: str, *, parent_id: int | None = None) -> list[dict[str, Any]]:
    """Tasks for a day. Top-level by default; pass parent_id for subtasks."""
    rows = connect().execute(
        "SELECT * FROM tasks WHERE day = ? AND parent_id IS ? ORDER BY sort_order, id",
        (day, parent_id),
    ).fetchall()
    return [_row_to_task(r) for r in rows]


def list_subtasks(parent_id: int) -> list[dict[str, Any]]:
    rows = connect().execute(
        "SELECT * FROM tasks WHERE parent_id = ? ORDER BY sort_order, id", (parent_id,)
    ).fetchall()
    return [_row_to_task(r) for r in rows]


def update_task(task_id: int, **fields: Any) -> None:
    allowed = {"text", "notes", "priority", "due_date", "tags", "day", "sort_order"}
    sets, values = [], []
    for key, value in fields.items():
        if key not in allowed:
            continue
        if key == "tags":
            value = json.dumps(sorted({t.strip().lower() for t in (value or []) if t.strip()}))
        sets.append(f"{key} = ?")
        values.append(value)
    if not sets:
        return
    conn = connect()
    values.append(task_id)
    conn.execute(f"UPDATE tasks SET {', '.join(sets)} WHERE id = ?", values)
    conn.commit()


def delete_task(task_id: int) -> None:
    task = get_task(task_id)
    if task is None:
        return
    conn = connect()
    # Explicit subtask delete: ON DELETE CASCADE needs the pragma on every
    # connection, and we would rather not depend on that.
    conn.execute("DELETE FROM tasks WHERE parent_id = ?", (task_id,))
    conn.execute("DELETE FROM xp_log WHERE task_id = ?", (task_id,))
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    _sync_sweep_bonus(task["day"])


def set_completed(task_id: int, completed: bool, *, streak: int = 0) -> int:
    """Complete or reopen a task, keeping the XP ledger in step. Returns XP delta."""
    task = get_task(task_id)
    if task is None or task["completed"] == completed:
        return 0
    conn = connect()
    now = datetime.now()
    before = total_xp()

    if completed:
        conn.execute(
            "UPDATE tasks SET completed = 1, completed_at = ? WHERE id = ?",
            (now.isoformat(timespec="seconds"), task_id),
        )
        conn.commit()
        # Subtasks are checklist steps: the parent task carries the points.
        if task["parent_id"] is None:
            points = int(round(config.BASE_XP[task["priority"]] * config.streak_multiplier(streak)))
            _log_xp(task["day"], task_id, points, f"{task['priority']} task")
            due = task.get("due_date")
            if due and now.date() <= date.fromisoformat(due):
                _log_xp(task["day"], task_id, config.EARLY_BONUS, "Ahead of due date")
    else:
        conn.execute(
            "UPDATE tasks SET completed = 0, completed_at = NULL WHERE id = ?", (task_id,)
        )
        # Reopening withdraws what completing it paid, but not the bonus for
        # having created it — that was earned when the quest was accepted and
        # the quest still exists.
        conn.execute(
            "DELETE FROM xp_log WHERE task_id = ? AND reason <> ?",
            (task_id, config.CREATE_REASON),
        )
        conn.commit()

    _sync_sweep_bonus(task["day"])
    return total_xp() - before


# ────── xp ──────

def _log_xp(day: str, task_id: int | None, points: int, reason: str) -> None:
    conn = connect()
    conn.execute(
        "INSERT INTO xp_log(day, task_id, points, reason, created_at) VALUES(?,?,?,?,?)",
        (day, task_id, points, reason, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()


def award_creation(day: str, task_id: int) -> int:
    """Award the flat bonus for accepting a new quest. Returns the points.

    Deliberately not inside add_task(): that is also how carried-over work,
    restored backups and checklist steps get written, and none of those are
    the user choosing to plan something. Only the capture box calls this.

    Deleting the quest removes the row with it (delete_task clears the ledger
    by task id), so create-and-delete cannot be farmed for points.
    """
    if config.CREATE_XP <= 0:
        return 0
    _log_xp(day, task_id, config.CREATE_XP, config.CREATE_REASON)
    return config.CREATE_XP


def _sync_sweep_bonus(day: str) -> None:
    """Grant or revoke the clean-sweep bonus so it always matches the board."""
    conn = connect()
    row = conn.execute(
        "SELECT COUNT(*) AS total, COALESCE(SUM(completed), 0) AS done "
        "FROM tasks WHERE day = ? AND parent_id IS NULL",
        (day,),
    ).fetchone()
    total, done = int(row["total"]), int(row["done"])
    earned = total >= config.SWEEP_MIN_TASKS and total == done
    held = conn.execute(
        "SELECT id FROM xp_log WHERE day = ? AND reason = 'Clean sweep'", (day,)
    ).fetchone()
    if earned and not held:
        _log_xp(day, None, config.SWEEP_BONUS, "Clean sweep")
    elif held and not earned:
        conn.execute("DELETE FROM xp_log WHERE day = ? AND reason = 'Clean sweep'", (day,))
        conn.commit()


def total_xp() -> int:
    row = connect().execute("SELECT COALESCE(SUM(points), 0) AS xp FROM xp_log").fetchone()
    return int(row["xp"])


def xp_for_day(day: str) -> int:
    row = connect().execute(
        "SELECT COALESCE(SUM(points), 0) AS xp FROM xp_log WHERE day = ?", (day,)
    ).fetchone()
    return int(row["xp"])


def xp_by_day(since: str) -> list[dict[str, Any]]:
    rows = connect().execute(
        "SELECT day, SUM(points) AS xp FROM xp_log WHERE day >= ? GROUP BY day ORDER BY day",
        (since,),
    ).fetchall()
    return [{"day": r["day"], "xp": int(r["xp"] or 0)} for r in rows]


# ────── streaks & carry-over ──────

def active_days() -> set[str]:
    """Days with at least one completed top-level task."""
    rows = connect().execute(
        "SELECT DISTINCT day FROM tasks WHERE completed = 1 AND parent_id IS NULL"
    ).fetchall()
    return {r["day"] for r in rows}


def current_streak(today: date | None = None, *, days: set[str] | None = None) -> int:
    """Consecutive active days ending today — or yesterday, if today is still young.

    A run is not broken until a whole day passes with nothing finished, so an
    untouched morning keeps yesterday's streak on the board.
    """
    today = today or date.today()
    days = active_days() if days is None else days
    anchor = today if today.isoformat() in days else today - timedelta(days=1)
    streak, cursor = 0, anchor
    while cursor.isoformat() in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def carry_over(today: date | None = None, lookback: int = 30) -> int:
    """Move unfinished work from previous days onto today. Idempotent per day.

    Only ever writes into *today* — never into whichever date is being browsed —
    and moves each task rather than copying it, so nothing multiplies.
    """
    today = today or date.today()
    today_str = today.isoformat()
    if get_setting("carried_through") == today_str:
        return 0

    conn = connect()
    existing = {
        r["text"].lower()
        for r in conn.execute(
            "SELECT text FROM tasks WHERE day = ? AND parent_id IS NULL", (today_str,)
        ).fetchall()
    }
    earliest = (today - timedelta(days=lookback)).isoformat()
    stale = conn.execute(
        "SELECT id, day, text FROM tasks WHERE completed = 0 AND parent_id IS NULL "
        "AND day >= ? AND day < ? ORDER BY day, sort_order",
        (earliest, today_str),
    ).fetchall()

    moved = 0
    for row in stale:
        if row["text"].lower() in existing:
            continue  # already on today's board under the same name
        conn.execute(
            "UPDATE tasks SET day = ?, carried_from = COALESCE(carried_from, ?) WHERE id = ? OR parent_id = ?",
            (today_str, row["day"], row["id"], row["id"]),
        )
        existing.add(row["text"].lower())
        moved += 1
    conn.commit()
    set_setting("carried_through", today_str)
    if moved:
        _sync_sweep_bonus(today_str)
    return moved


# ────── stats ──────

def day_summary(day: str) -> dict[str, int]:
    row = connect().execute(
        "SELECT COUNT(*) AS total, COALESCE(SUM(completed), 0) AS done "
        "FROM tasks WHERE day = ? AND parent_id IS NULL",
        (day,),
    ).fetchone()
    total, done = int(row["total"]), int(row["done"])
    return {"total": total, "done": done, "open": total - done,
            "score": int(done / total * 100) if total else 0}


def completions_by_day(since: str) -> list[dict[str, Any]]:
    rows = connect().execute(
        "SELECT day, COUNT(*) AS total, COALESCE(SUM(completed), 0) AS done "
        "FROM tasks WHERE day >= ? AND parent_id IS NULL GROUP BY day ORDER BY day",
        (since,),
    ).fetchall()
    return [{"day": r["day"], "total": int(r["total"]), "done": int(r["done"])} for r in rows]


def priority_breakdown(since: str) -> list[dict[str, Any]]:
    rows = connect().execute(
        "SELECT priority, COUNT(*) AS total, COALESCE(SUM(completed), 0) AS done "
        "FROM tasks WHERE day >= ? AND parent_id IS NULL GROUP BY priority",
        (since,),
    ).fetchall()
    return [{"priority": r["priority"], "total": int(r["total"]), "done": int(r["done"])}
            for r in rows]


def all_tags() -> list[str]:
    rows = connect().execute("SELECT tags FROM tasks").fetchall()
    seen: set[str] = set()
    for row in rows:
        try:
            seen.update(json.loads(row["tags"]) or [])
        except (json.JSONDecodeError, TypeError):
            continue
    return sorted(seen)


# ────── backup ──────

def export_state() -> dict[str, Any]:
    conn = connect()
    return {
        "version": 2,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "settings": {r["key"]: r["value"]
                     for r in conn.execute("SELECT * FROM settings").fetchall()},
        "tasks": [dict(r) for r in conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()],
        "xp_log": [dict(r) for r in conn.execute("SELECT * FROM xp_log ORDER BY id").fetchall()],
    }


def import_state(payload: dict[str, Any]) -> int:
    """Replace all data with a backup. Understands the old v1 JSON format too."""
    conn = connect()
    conn.execute("DELETE FROM xp_log")
    conn.execute("DELETE FROM tasks")
    conn.execute("DELETE FROM settings")
    conn.commit()

    if payload.get("version") == 2:
        task_cols = ("id", "parent_id", "day", "text", "notes", "priority", "completed",
                     "completed_at", "due_date", "tags", "sort_order", "created_at",
                     "carried_from")
        xp_cols = ("id", "day", "task_id", "points", "reason", "created_at")
        # Parents must land before the children that reference them.
        tasks = sorted(payload.get("tasks", []), key=lambda t: (t.get("parent_id") is not None,
                                                               t.get("id") or 0))
        for task in tasks:
            conn.execute(
                f"INSERT INTO tasks({', '.join(task_cols)}) "
                f"VALUES({','.join('?' * len(task_cols))})",
                [task.get(c) for c in task_cols],
            )
        for entry in payload.get("xp_log", []):
            conn.execute(
                f"INSERT INTO xp_log({', '.join(xp_cols)}) "
                f"VALUES({','.join('?' * len(xp_cols))})",
                [entry.get(c) for c in xp_cols],
            )
        for key, value in (payload.get("settings") or {}).items():
            conn.execute("INSERT INTO settings(key, value) VALUES(?,?)", (key, value))
        conn.commit()
        conn.resync_sequences()
        return len(payload.get("tasks", []))

    return _import_legacy(payload)


def _import_legacy(payload: dict[str, Any]) -> int:
    """Import the original session_state backup: {tasks_by_date, user_name, ...}."""
    count = 0
    for day, tasks in (payload.get("tasks_by_date") or {}).items():
        for task in tasks:
            if not isinstance(task, dict) or not str(task.get("text", "")).strip():
                continue
            task_id = add_task(
                day, str(task["text"]),
                task.get("priority", "Medium"),
                notes=str(task.get("notes") or ""),
            )
            if task.get("completed"):
                conn = connect()
                conn.execute(
                    "UPDATE tasks SET completed = 1, completed_at = ? WHERE id = ?",
                    (f"{day}T12:00:00", task_id),
                )
                conn.commit()
                _log_xp(day, task_id, config.BASE_XP.get(task.get("priority", "Medium"), 20),
                        f"{task.get('priority', 'Medium')} task")
            count += 1
    if payload.get("user_name"):
        set_setting("user_name", str(payload["user_name"]))
    if payload.get("theme"):
        set_setting("theme", str(payload["theme"]))
    for day in (payload.get("tasks_by_date") or {}):
        _sync_sweep_bonus(day)
    return count
