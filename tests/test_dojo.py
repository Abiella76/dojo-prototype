"""Unit tests for the parts that used to be silently wrong."""

from __future__ import annotations

import os
import tempfile
from datetime import date, timedelta

import pytest

os.environ["DOJO_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")

from dojo import config, db, gamify, nlp  # noqa: E402

# Every test runs twice: once on SQLite, once on Postgres. The Postgres pass
# skips unless DOJO_TEST_PG_URL points at a throwaway database — CI supplies
# one from a service container. Running the identical assertions on both is
# what keeps the two backends honest with each other.
PG_URL = os.environ.get("DOJO_TEST_PG_URL", "").strip()
BACKENDS = ["sqlite", "postgres"]


@pytest.fixture(autouse=True, params=BACKENDS)
def fresh_db(request, tmp_path, monkeypatch):
    if request.param == "postgres":
        if not PG_URL:
            pytest.skip("set DOJO_TEST_PG_URL to exercise the Postgres backend")
        monkeypatch.setenv("DATABASE_URL", PG_URL)
        db.reset_connection()
        conn = db.connect()
        for table in ("xp_log", "tasks", "settings"):
            conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        conn.commit()
        db.reset_connection()
        db.connect()  # recreates the schema empty
    else:
        for var in ("DATABASE_URL", "NEON_DATABASE_URL"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setattr(config, "DB_PATH", tmp_path / "dojo.db")
        db.reset_connection()
        db.connect()
    yield
    db.reset_connection()


def test_backend_is_the_one_under_test(request):
    expected = request.node.callspec.params["fresh_db"]
    assert db.backend() == expected


# ────── persistence ──────

def test_tasks_survive_a_new_connection():
    db.add_task("2026-09-02", "write the thing", "High")
    db.reset_connection()
    assert [t["text"] for t in db.list_tasks("2026-09-02")] == ["write the thing"]


def test_identical_tasks_are_addressed_independently():
    """The old code used list.index(), which matched by value and hit the wrong row."""
    first = db.add_task("2026-09-02", "email", "Low")
    second = db.add_task("2026-09-02", "email", "Low")
    assert first != second
    db.delete_task(first)
    remaining = db.list_tasks("2026-09-02")
    assert len(remaining) == 1 and remaining[0]["id"] == second


def test_notes_and_tags_round_trip():
    task_id = db.add_task("2026-09-02", "x", tags=["Work", " work ", "home"])
    db.update_task(task_id, notes="line one\nline two")
    task = db.get_task(task_id)
    assert task["tags"] == ["home", "work"]  # deduped, lowercased, sorted
    assert task["notes"] == "line one\nline two"


# ────── xp ──────

def test_xp_matches_priority_and_reverses_on_reopen():
    task_id = db.add_task("2026-09-02", "big one", "Critical")
    assert db.set_completed(task_id, True) == config.BASE_XP["Critical"]
    assert db.total_xp() == 50
    assert db.set_completed(task_id, False) == -50
    assert db.total_xp() == 0


def test_streak_multiplier_and_early_bonus():
    due = (date.today() + timedelta(days=2)).isoformat()
    task_id = db.add_task(date.today().isoformat(), "ship", "High", due_date=due)
    gained = db.set_completed(task_id, True, streak=7)
    assert gained == int(round(30 * 1.5)) + config.EARLY_BONUS


def test_clean_sweep_is_granted_and_revoked():
    day = "2026-09-02"
    ids = [db.add_task(day, f"task {i}", "Low") for i in range(3)]
    for task_id in ids:
        db.set_completed(task_id, True)
    assert db.xp_for_day(day) == 3 * 10 + config.SWEEP_BONUS
    db.set_completed(ids[0], False)  # board no longer clear
    assert db.xp_for_day(day) == 2 * 10


def test_adding_a_task_revokes_a_held_sweep():
    day = "2026-09-02"
    for i in range(3):
        db.set_completed(db.add_task(day, f"t{i}", "Low"), True)
    assert db.xp_for_day(day) == 55
    db.add_task(day, "one more", "Low")
    assert db.xp_for_day(day) == 30


def test_subtasks_earn_no_xp_of_their_own():
    parent = db.add_task("2026-09-02", "parent", "High")
    child = db.add_task("2026-09-02", "step", "High", parent_id=parent)
    db.set_completed(child, True)
    assert db.total_xp() == 0
    assert db.day_summary("2026-09-02")["total"] == 1  # subtasks stay off the board count


def test_deleting_a_parent_removes_its_steps_and_ledger():
    parent = db.add_task("2026-09-02", "parent", "High")
    db.add_task("2026-09-02", "step", "High", parent_id=parent)
    db.set_completed(parent, True)
    db.delete_task(parent)
    assert db.list_tasks("2026-09-02") == []
    assert db.list_subtasks(parent) == []
    assert db.total_xp() == 0


# ────── streaks ──────

def test_streak_survives_an_untouched_morning():
    """The old streak read 0 every morning until the first task was finished."""
    today = date.today()
    for offset in (1, 2, 3):
        day = (today - timedelta(days=offset)).isoformat()
        db.set_completed(db.add_task(day, f"t{offset}", "Low"), True)
    assert db.current_streak(today) == 3


def test_streak_breaks_after_a_blank_day():
    today = date.today()
    for offset in (2, 3):
        day = (today - timedelta(days=offset)).isoformat()
        db.set_completed(db.add_task(day, f"t{offset}", "Low"), True)
    assert db.current_streak(today) == 0


# ────── carry-over ──────

def test_carry_over_moves_into_today_and_is_idempotent():
    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    db.add_task(yesterday, "unfinished", "High")
    db.set_completed(db.add_task(yesterday, "finished", "Low"), True)

    assert db.carry_over(today) == 1
    assert [t["text"] for t in db.list_tasks(today.isoformat())] == ["unfinished"]
    assert [t["text"] for t in db.list_tasks(yesterday)] == ["finished"]

    db.set_setting("carried_through", "")
    assert db.carry_over(today) == 0  # already there, not duplicated
    assert len(db.list_tasks(today.isoformat())) == 1


def test_browsing_an_old_day_never_mutates_it():
    """The original wrote carried tasks into whichever date you were viewing."""
    today = date.today()
    old = (today - timedelta(days=5)).isoformat()
    older = (today - timedelta(days=9)).isoformat()
    db.add_task(older, "ancient", "Low")
    db.carry_over(today)
    assert db.list_tasks(old) == []


def test_carry_over_brings_subtasks_along():
    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    parent = db.add_task(yesterday, "parent", "High")
    db.add_task(yesterday, "step", "High", parent_id=parent)
    db.carry_over(today)
    assert db.get_task(parent)["day"] == today.isoformat()
    assert db.list_subtasks(parent)[0]["day"] == today.isoformat()


# ────── parsing ──────

@pytest.mark.parametrize("raw,expected_text,expected_priority,expected_tags", [
    ("call the dentist tomorrow #health !high", "call the dentist", "High", ["health"]),
    ("file taxes by 2026-09-15 !critical #admin", "file taxes", "Critical", ["admin"]),
    ("buy milk", "buy milk", None, []),
])
def test_parse_task(raw, expected_text, expected_priority, expected_tags):
    parsed = nlp.parse_task(raw, today=date(2026, 9, 2))
    assert parsed["text"] == expected_text
    assert parsed["priority"] == expected_priority
    assert parsed["tags"] == expected_tags


def test_parse_relative_dates():
    today = date(2026, 9, 2)  # Wednesday
    assert nlp.parse_task("gym tomorrow", today=today)["due_date"] == "2026-09-03"
    assert nlp.parse_task("gym friday", today=today)["due_date"] == "2026-09-04"
    assert nlp.parse_task("gym in 2 weeks", today=today)["due_date"] == "2026-09-16"
    assert nlp.parse_task("gym", today=today)["due_date"] is None


def test_parse_never_returns_empty_text():
    assert nlp.parse_task("#work !high", today=date(2026, 9, 2))["text"] == "#work !high"


# ────── belts ──────

def test_belts_climb_with_xp():
    assert config.belt_for_xp(0)[0] == "White"
    assert config.belt_for_xp(250)[0] == "Yellow"
    assert config.belt_for_xp(14000)[:2] == ("Black", 8)
    assert config.belt_for_xp(999999)[3] is None
    assert 0.0 <= config.belt_progress(1234) <= 1.0


def test_xp_preview_matches_what_is_awarded():
    day = date.today().isoformat()
    due = (date.today() + timedelta(days=1)).isoformat()
    preview = gamify.xp_preview("Critical", 7, due_date=due)
    task_id = db.add_task(day, "match me", "Critical", due_date=due)
    assert db.set_completed(task_id, True, streak=7) == preview["total"]


# ────── backup ──────

def test_export_import_round_trip():
    day = "2026-09-02"
    task_id = db.add_task(day, "keep me", "High", tags=["work"], notes="hello")
    db.add_task(day, "step", "High", parent_id=task_id)
    db.set_completed(task_id, True)
    snapshot = db.export_state()
    before_xp = db.total_xp()

    db.import_state(snapshot)
    assert db.total_xp() == before_xp
    restored = db.list_tasks(day)
    assert len(restored) == 1 and restored[0]["notes"] == "hello"
    assert restored[0]["tags"] == ["work"]
    assert len(db.list_subtasks(restored[0]["id"])) == 1


def test_legacy_backup_imports():
    """The v1 format written by the original session_state app."""
    legacy = {
        "user_name": "Alex",
        "theme": "dark",
        "tasks_by_date": {
            "2026-08-30": [
                {"text": "old task", "completed": True, "notes": "n", "priority": "High"},
                {"text": "still open", "completed": False, "notes": "", "priority": "Low"},
            ]
        },
    }
    assert db.import_state(legacy) == 2
    assert db.get_setting("user_name") == "Alex"
    tasks = db.list_tasks("2026-08-30")
    assert {t["text"] for t in tasks} == {"old task", "still open"}
    assert db.total_xp() == config.BASE_XP["High"]


def test_accepting_a_quest_awards_the_creation_bonus():
    day = "2026-09-02"
    task_id = db.add_task(day, "plan something", "Low")
    assert db.total_xp() == 0            # add_task alone never pays
    assert db.award_creation(day, task_id) == config.CREATE_XP
    assert db.total_xp() == config.CREATE_XP
    assert db.xp_for_day(day) == config.CREATE_XP


def test_creation_bonus_survives_completing_and_reopening():
    """Reopening withdraws what finishing paid, not the bonus for creating it."""
    day = "2026-09-02"
    task_id = db.add_task(day, "round trip", "Critical")
    db.award_creation(day, task_id)
    db.set_completed(task_id, True)
    assert db.total_xp() == config.CREATE_XP + config.BASE_XP["Critical"]
    db.set_completed(task_id, False)
    assert db.total_xp() == config.CREATE_XP


def test_deleting_a_quest_takes_its_creation_bonus_with_it():
    """Otherwise create-and-delete would be a points faucet."""
    day = "2026-09-02"
    for _ in range(5):
        db.award_creation(day, db.add_task(day, "churn", "Low"))
    assert db.total_xp() == 5 * config.CREATE_XP
    for task in db.list_tasks(day):
        db.delete_task(task["id"])
    assert db.total_xp() == 0


def test_creation_bonus_is_not_paid_for_checklist_steps():
    """Only the capture box awards it; subtasks and restores go through add_task."""
    parent = db.add_task("2026-09-02", "parent", "High")
    db.add_task("2026-09-02", "step", "High", parent_id=parent)
    assert db.total_xp() == 0
