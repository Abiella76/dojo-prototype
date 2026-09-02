"""Deterministic natural-language parsing for quick task entry.

Runs with no API key and no network. `ai.py` layers an LLM on top for the
phrasings this cannot reach, but this parser is always the first pass so the
common cases stay instant and free.

    "call the dentist tomorrow #health !high"
      -> text="call the dentist", due=<tomorrow>, tags=["health"], priority="High"
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from .config import PRIORITIES

# !critical / !high / !med / !c / !1 ...
_PRIORITY_ALIASES = {
    "critical": "Critical", "crit": "Critical", "c": "Critical", "1": "Critical", "urgent": "Critical",
    "high": "High", "h": "High", "2": "High",
    "medium": "Medium", "med": "Medium", "m": "Medium", "3": "Medium", "normal": "Medium",
    "low": "Low", "l": "Low", "4": "Low",
}

_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

_TAG_RE = re.compile(r"(?:^|\s)#([\w-]{1,30})\b")
_PRIORITY_RE = re.compile(r"(?:^|\s)!([A-Za-z0-9]{1,8})\b")
_ISO_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_IN_DAYS_RE = re.compile(r"\bin (\d{1,3}) (day|days|week|weeks)\b", re.I)
_NEXT_WEEKDAY_RE = re.compile(r"\b(?:next |this |on )?(" + "|".join(_WEEKDAYS) + r")\b", re.I)
_MONTH_DAY_RE = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]* (\d{1,2})(?:st|nd|rd|th)?\b", re.I
)
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

# Filler that only ever introduced a date; dropped once the date is extracted.
_TRAILING_FILLER = re.compile(r"\s*\b(by|due|on|before|until)\s*$", re.I)


def _next_weekday(today: date, target: int, *, force_next: bool) -> date:
    delta = (target - today.weekday()) % 7
    if delta == 0 or force_next:
        delta = delta or 7
        if force_next and delta < 7 and (target - today.weekday()) % 7 == 0:
            delta = 7
    return today + timedelta(days=delta)


def parse_task(raw: str, *, today: date | None = None) -> dict:
    """Split a quick-entry string into structured task fields.

    Always returns a dict with text / priority / due_date / tags; `priority` is
    None when the string did not name one, so callers can fall back to a
    default or ask the model for a suggestion.
    """
    today = today or date.today()
    text = raw.strip()
    tags: list[str] = []
    priority: str | None = None
    due: date | None = None

    for match in _TAG_RE.finditer(text):
        tags.append(match.group(1).lower())
    text = _TAG_RE.sub(" ", text)

    match = _PRIORITY_RE.search(text)
    if match:
        candidate = _PRIORITY_ALIASES.get(match.group(1).lower())
        if candidate:
            priority = candidate
            text = text[: match.start()] + " " + text[match.end():]

    # Dates, most explicit first.
    match = _ISO_RE.search(text)
    if match:
        try:
            due = date.fromisoformat(match.group(1))
            text = text[: match.start()] + " " + text[match.end():]
        except ValueError:
            pass

    if due is None:
        match = _MONTH_DAY_RE.search(text)
        if match:
            month = _MONTHS[match.group(1)[:3].lower()]
            try:
                candidate = date(today.year, month, int(match.group(2)))
                if candidate < today:
                    candidate = date(today.year + 1, month, int(match.group(2)))
                due = candidate
                text = text[: match.start()] + " " + text[match.end():]
            except ValueError:
                pass

    if due is None:
        match = _IN_DAYS_RE.search(text)
        if match:
            count = int(match.group(1))
            due = today + timedelta(days=count * (7 if match.group(2).lower().startswith("week") else 1))
            text = text[: match.start()] + " " + text[match.end():]

    if due is None:
        lowered = text.lower()
        for word, offset in (("today", 0), ("tonight", 0), ("tomorrow", 1), ("tmr", 1), ("tmrw", 1)):
            idx = lowered.find(word)
            if idx != -1 and (idx == 0 or not lowered[idx - 1].isalnum()):
                end = idx + len(word)
                if end == len(lowered) or not lowered[end].isalnum():
                    due = today + timedelta(days=offset)
                    text = text[:idx] + " " + text[end:]
                    break

    if due is None:
        match = _NEXT_WEEKDAY_RE.search(text)
        if match:
            force_next = "next" in text[max(0, match.start() - 5): match.start()].lower()
            due = _next_weekday(today, _WEEKDAYS.index(match.group(1).lower()), force_next=force_next)
            text = text[: match.start()] + " " + text[match.end():]

    text = _TRAILING_FILLER.sub("", re.sub(r"\s{2,}", " ", text).strip())
    return {
        "text": text.strip(" -,") or raw.strip(),
        "priority": priority,
        "due_date": due.isoformat() if due else None,
        "tags": sorted(dict.fromkeys(tags)),
    }


def suggest_priority(text: str) -> str:
    """Cheap keyword heuristic used when no model is configured."""
    lowered = text.lower()
    if any(w in lowered for w in ("urgent", "asap", "emergency", "deadline", "overdue", "critical", "tax", "rent")):
        return "Critical"
    if any(w in lowered for w in ("important", "meeting", "call", "submit", "send", "pay", "book", "doctor", "interview")):
        return "High"
    if any(w in lowered for w in ("maybe", "someday", "idea", "read", "browse", "watch", "tidy")):
        return "Low"
    return "Medium"


assert set(_PRIORITY_ALIASES.values()) == set(PRIORITIES)
