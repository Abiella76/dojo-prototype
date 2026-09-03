"""Optional LLM assist.

Every function here degrades gracefully: with no API key configured the app
falls back to the deterministic helpers in `nlp.py` and nothing breaks. Set
OPENAI_API_KEY (or add it to `.streamlit/secrets.toml`) to switch the smart
paths on. OPENAI_MODEL overrides the default model.
"""

from __future__ import annotations

import json
import os
from datetime import date
from typing import Any

from . import nlp
from .config import PRIORITIES

DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
_TIMEOUT = 20.0


def api_key(explicit: str | None = None) -> str | None:
    return (explicit or os.environ.get("OPENAI_API_KEY") or "").strip() or None


def available(key: str | None = None) -> bool:
    if api_key(key) is None:
        return False
    try:
        import openai  # noqa: F401
    except ImportError:
        return False
    return True


def _client(key: str | None):
    from openai import OpenAI

    return OpenAI(api_key=api_key(key), timeout=_TIMEOUT)


def _ask_json(prompt: str, system: str, key: str | None) -> dict[str, Any] | None:
    """One JSON-mode round trip. Returns None on any failure — never raises."""
    try:
        response = _client(key).chat.completions.create(
            model=DEFAULT_MODEL,
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=600,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return json.loads(response.choices[0].message.content or "{}")
    except Exception:  # network, auth, quota, malformed JSON — all non-fatal
        return None


# ────── task capture ──────

_PARSE_SYSTEM = (
    "You turn a scribbled to-do into structured JSON. Reply with only a JSON object "
    'shaped {"text": str, "priority": one of ["Critical","High","Medium","Low"], '
    '"due_date": "YYYY-MM-DD" or null, "tags": [str], "subtasks": [str]}. '
    "Keep `text` a short imperative phrase with dates and tags stripped out. "
    "Use at most 3 lowercase single-word tags. Suggest subtasks only when the task "
    "genuinely has separable steps; otherwise return an empty list."
)


def parse_task(raw: str, *, key: str | None = None, today: date | None = None) -> dict[str, Any]:
    """Parse quick-entry text, using the model when configured.

    The deterministic parse always runs first and anything it found explicitly
    (an `!priority`, a `#tag`, a real date) wins — the model only fills gaps.
    """
    today = today or date.today()
    base = nlp.parse_task(raw, today=today)
    base["subtasks"] = []
    base["source"] = "rules"

    if not available(key):
        base["priority"] = base["priority"] or nlp.suggest_priority(base["text"])
        return base

    data = _ask_json(f"Today is {today.isoformat()}.\nTo-do: {raw}", _PARSE_SYSTEM, key)
    if not data:
        base["priority"] = base["priority"] or nlp.suggest_priority(base["text"])
        return base

    base["source"] = "ai"
    if not base["priority"]:
        candidate = str(data.get("priority", "")).title()
        base["priority"] = candidate if candidate in PRIORITIES else nlp.suggest_priority(base["text"])
    if not base["due_date"] and data.get("due_date"):
        try:
            base["due_date"] = date.fromisoformat(str(data["due_date"])).isoformat()
        except (ValueError, TypeError):
            pass
    if not base["tags"]:
        base["tags"] = [str(t).lower().strip() for t in (data.get("tags") or [])][:3]
    if isinstance(data.get("text"), str) and data["text"].strip():
        base["text"] = data["text"].strip()
    base["subtasks"] = [str(s).strip() for s in (data.get("subtasks") or []) if str(s).strip()][:6]
    return base


_BREAKDOWN_SYSTEM = (
    "Break a task into 2-5 concrete, ordered steps. Reply with only "
    '{"subtasks": [str]}. Each step is a short imperative phrase.'
)


def suggest_subtasks(text: str, *, key: str | None = None) -> list[str]:
    if not available(key):
        return []
    data = _ask_json(f"Task: {text}", _BREAKDOWN_SYSTEM, key) or {}
    return [str(s).strip() for s in (data.get("subtasks") or []) if str(s).strip()][:5]


# ────── daily briefing ──────

_PLAN_SYSTEM = (
    "You are a terse, encouraging training coach for a personal task app. "
    'Reply with only {"headline": str, "order": [str], "note": str}. '
    "`headline` is under 12 words. `order` lists the open task titles, verbatim, in "
    "the sequence you would tackle them. `note` is one sentence of practical advice. "
    "No emoji, no filler, no praise for its own sake."
)


def daily_briefing(open_tasks: list[dict], stats: dict, *, key: str | None = None) -> dict[str, Any] | None:
    """A short plan for the day. Returns None when unavailable."""
    if not available(key) or not open_tasks:
        return None
    lines = [
        f"- {t['text']} [{t['priority']}]"
        + (f" due {t['due_date']}" if t.get("due_date") else "")
        + (f" tags: {', '.join(t['tags'])}" if t.get("tags") else "")
        for t in open_tasks[:20]
    ]
    prompt = (
        f"Streak: {stats.get('streak', 0)} days. Finished today: "
        f"{stats.get('done', 0)}/{stats.get('total', 0)}.\nOpen tasks:\n" + "\n".join(lines)
    )
    data = _ask_json(prompt, _PLAN_SYSTEM, key)
    if not data:
        return None
    titles = {t["text"] for t in open_tasks}
    data["order"] = [t for t in (data.get("order") or []) if t in titles]
    return data


def fallback_order(open_tasks: list[dict]) -> list[dict]:
    """Rule-based ordering used when no model is configured: overdue, then priority."""
    rank = {p: i for i, p in enumerate(PRIORITIES)}
    today_str = date.today().isoformat()

    def sort_key(task: dict) -> tuple:
        due = task.get("due_date")
        return (0 if due and due <= today_str else 1, due or "9999-12-31",
                rank.get(task.get("priority", "Medium"), 9))

    return sorted(open_tasks, key=sort_key)
