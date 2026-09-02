"""The daily board: quick capture, filters, task cards, coach panel."""

from __future__ import annotations

from datetime import date

import streamlit as st

from .. import ai, db, gamify
from ..config import PRIORITIES
from . import components as c


def _rerun() -> None:
    st.rerun()


# ────── capture ──────

def quick_add(day: str, api_key: str | None) -> None:
    with st.form("quick_add", clear_on_submit=True, border=False):
        cols = st.columns([6, 3, 1.4])
        with cols[0]:
            raw = st.text_input(
                "New task", placeholder="e.g. call the dentist tomorrow #health !high",
                label_visibility="collapsed",
            )
        with cols[1]:
            choice = st.selectbox(
                "Priority", ["Auto", *PRIORITIES], label_visibility="collapsed",
                help="Auto reads !high / !critical from the text, or infers one.",
            )
        with cols[2]:
            submitted = st.form_submit_button("Add", type="primary", width="stretch")

    smart = "on" if ai.available(api_key) else "off"
    st.caption(
        f"Type naturally — `tomorrow`, `next friday`, `#tag`, `!critical` are all understood. "
        f"AI assist: **{smart}**."
    )

    if submitted and raw.strip():
        parsed = ai.parse_task(raw, key=api_key)
        priority = choice if choice != "Auto" else (parsed["priority"] or "Medium")
        task_id = db.add_task(
            day, parsed["text"], priority,
            due_date=parsed["due_date"], tags=parsed["tags"],
        )
        for step in parsed.get("subtasks", []):
            db.add_task(day, step, priority, parent_id=task_id)
        bits = [priority]
        if parsed["due_date"]:
            bits.append(f"due {parsed['due_date']}")
        if parsed["tags"]:
            bits.append(" ".join(f"#{t}" for t in parsed["tags"]))
        st.toast(f"Added — {' · '.join(bits)}")
        _rerun()
    elif submitted:
        st.warning("Nothing to add — type a task first.")


# ────── filters ──────

def filter_bar(tasks: list[dict]) -> list[dict]:
    tags = sorted({t for task in tasks for t in task.get("tags") or []})
    cols = st.columns([2.2, 2.2, 2.6, 3])
    with cols[0]:
        status = st.segmented_control(
            "Status", ["All", "Open", "Done"], default="All",
            key="f_status", label_visibility="collapsed",
        ) or "All"
    with cols[1]:
        priority = st.selectbox("Priority", ["Any priority", *PRIORITIES],
                                key="f_prio", label_visibility="collapsed")
    with cols[2]:
        tag = st.selectbox("Tag", ["Any tag", *[f"#{t}" for t in tags]],
                           key="f_tag", label_visibility="collapsed")
    with cols[3]:
        query = st.text_input("Search", placeholder="Search tasks…",
                              key="f_query", label_visibility="collapsed")

    out = tasks
    if status == "Open":
        out = [t for t in out if not t["completed"]]
    elif status == "Done":
        out = [t for t in out if t["completed"]]
    if priority != "Any priority":
        out = [t for t in out if t["priority"] == priority]
    if tag != "Any tag":
        out = [t for t in out if tag.lstrip("#") in (t.get("tags") or [])]
    if query.strip():
        needle = query.strip().lower()
        out = [t for t in out
               if needle in t["text"].lower() or needle in (t.get("notes") or "").lower()]
    return out


# ────── one task card ──────

def _subtask_panel(task: dict, api_key: str | None) -> None:
    subs = db.list_subtasks(task["id"])
    for sub in subs:
        row = st.columns([8, 1.4])
        with row[0]:
            checked = st.checkbox(
                sub["text"], value=sub["completed"], key=f"sub_{sub['id']}",
            )
            if checked != sub["completed"]:
                db.set_completed(sub["id"], checked)
                _rerun()
        with row[1]:
            if st.button("✕", key=f"subdel_{sub['id']}", help="Remove step"):
                db.delete_task(sub["id"])
                _rerun()

    with st.form(f"addsub_{task['id']}", clear_on_submit=True, border=False):
        text = st.text_input("Step", placeholder="Add a step…",
                             label_visibility="collapsed")
        if st.form_submit_button("Add step", width="stretch") and text.strip():
            db.add_task(task["day"], text, task["priority"], parent_id=task["id"])
            _rerun()

    if ai.available(api_key) and not subs:
        if st.button("Suggest steps", key=f"aisub_{task['id']}"):
            with st.spinner("Thinking…"):
                steps = ai.suggest_subtasks(task["text"], key=api_key)
            if steps:
                for step in steps:
                    db.add_task(task["day"], step, task["priority"], parent_id=task["id"])
                _rerun()
            else:
                st.info("No suggestions came back.")


def _edit_panel(task: dict) -> None:
    with st.form(f"edit_{task['id']}", border=False):
        text = st.text_input("Task", value=task["text"])
        row = st.columns(2)
        with row[0]:
            priority = st.selectbox("Priority", PRIORITIES,
                                    index=PRIORITIES.index(task["priority"]))
        with row[1]:
            current_due = date.fromisoformat(task["due_date"]) if task.get("due_date") else None
            due = st.date_input("Due date", value=current_due, format="YYYY-MM-DD")
        tags = st.text_input("Tags", value=" ".join(f"#{t}" for t in task.get("tags") or []),
                             placeholder="#work #urgent")
        clear_due = st.checkbox("No due date", value=task.get("due_date") is None)
        if st.form_submit_button("Save changes", type="primary") and text.strip():
            db.update_task(
                task["id"], text=text.strip(), priority=priority,
                due_date=None if clear_due or due is None else due.isoformat(),
                tags=[t.lstrip("#") for t in tags.split()],
            )
            st.toast("Task updated")
            _rerun()


def task_card(task: dict, streak: int, api_key: str | None, today: date) -> None:
    subs = db.list_subtasks(task["id"])
    sub_done = sum(1 for s in subs if s["completed"])

    with st.container(border=True, key=f"card-task-{task['id']}"):
        c.task_header(task, today=today, sub_done=sub_done, sub_total=len(subs))

        cols = st.columns([2.1, 1.5, 1.4, 1.6, 1.2, 2.7])
        with cols[0]:
            if task["completed"]:
                if st.button("Reopen", key=f"reopen_{task['id']}", width="stretch"):
                    db.set_completed(task["id"], False)
                    _rerun()
            else:
                if st.button("Complete", key=f"done_{task['id']}", type="primary",
                             width="stretch"):
                    before_level = gamify.lifetime_stats()["level"]
                    gained = db.set_completed(task["id"], True, streak=streak)
                    after = gamify.lifetime_stats()
                    st.toast(f"+{gained} XP — {after['xp']:,} total")
                    if after["level"] > before_level:
                        st.balloons()
                        st.session_state["belt_up"] = after["belt"]
                    _rerun()

        with cols[1]:
            label = f"Steps {sub_done}/{len(subs)}" if subs else "Steps"
            with st.popover(label, width="stretch"):
                _subtask_panel(task, api_key)

        with cols[2]:
            with st.popover("Notes", width="stretch"):
                with st.form(f"note_{task['id']}", border=False):
                    note = st.text_area("Note", value=task.get("notes") or "",
                                        height=140, label_visibility="collapsed")
                    if st.form_submit_button("Save note", type="primary"):
                        db.update_task(task["id"], notes=note.strip())
                        _rerun()

        with cols[3]:
            with st.popover("Edit", width="stretch"):
                _edit_panel(task)

        with cols[4]:
            with st.popover("⋯", width="stretch"):
                st.caption("Delete this task and its steps?")
                if st.button("Delete", key=f"del_{task['id']}", width="stretch"):
                    db.delete_task(task["id"])
                    st.toast("Task deleted")
                    _rerun()

        if not task["completed"]:
            preview = gamify.xp_preview(task["priority"], streak,
                                        due_date=task.get("due_date"), today=today)
            with cols[5]:
                st.markdown(
                    f"<span class='sub-progress'>worth {preview['total']} XP</span>",
                    unsafe_allow_html=True,
                )

        if task.get("notes"):
            c.note_block(task["notes"])


# ────── coach ──────

def coach_panel(open_tasks: list[dict], stats: dict, api_key: str | None) -> None:
    if not open_tasks:
        st.success("Board clear. Nothing open for this day.")
        return

    with st.container(border=True, key="card-coach"):
        if ai.available(api_key):
            if st.button("Plan my day", key="plan_btn"):
                with st.spinner("Reading your board…"):
                    st.session_state["briefing"] = ai.daily_briefing(
                        open_tasks, stats, key=api_key)
            brief = st.session_state.get("briefing")
            if brief:
                st.markdown(f"**{c.esc(brief.get('headline', 'Your plan'))}**")
                for i, title in enumerate(brief.get("order", []), 1):
                    st.markdown(f"{i}. {c.esc(title)}")
                if brief.get("note"):
                    c.note_block(brief["note"])
                return
            st.caption("Ask the coach to sequence today's board.")
        else:
            st.markdown("**Suggested order**")
            for i, task in enumerate(ai.fallback_order(open_tasks)[:5], 1):
                due = f" · due {task['due_date']}" if task.get("due_date") else ""
                st.markdown(f"{i}. {c.esc(task['text'])} — {task['priority']}{due}")
            st.caption("Overdue first, then by priority. Set OPENAI_API_KEY for AI planning.")
