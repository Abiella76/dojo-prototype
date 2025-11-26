import streamlit as st
from datetime import date, timedelta

st.set_page_config(page_title="Dojo", page_icon="Calendar", layout="wide")

# Theme
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
bg = "#0e1117" if st.session_state.theme == "dark" else "#ffffff"
text = "#fafafa" if st.session_state.theme == "dark" else "#000000"
accent = "#ff4b4b"

PRIORITY_COLORS = {"Critical": "#ff3333", "High": "#ff8833", "Medium": "#ffdd33", "Low": "#33ff99"}
PRIORITIES = ["Critical", "High", "Medium", "Low"]

# Data
if "user_name" not in st.session_state:
    st.session_state.user_name = "Warrior"
if "tasks_by_date" not in st.session_state:
    st.session_state.tasks_by_date = {}

if st.session_state.user_name == "Warrior":
    name = st.text_input("Your name?", placeholder="e.g. Alex")
    if st.button("Enter Dojo") or name:
        st.session_state.user_name = name.strip() or "Warrior"
        st.balloons()
        st.rerun()

today = date.today()
selected_date = st.date_input("Day", value=today)
date_str = selected_date.strftime("%Y-%m-%d")
if date_str not in st.session_state.tasks_by_date:
    st.session_state.tasks_by_date[date_str] = []

# Carry-over
for offset in range(1, 31):
    past = (today - timedelta(days=offset)).strftime("%Y-%m-%d")
    if past in st.session_state.tasks_by_date:
        for t in st.session_state.tasks_by_date[past]:
            if not t.get("completed") and t["text"] not in [x["text"] for x in st.session_state.tasks_by_date.get(date_str, [])]:
                st.session_state.tasks_by_date[date_str].append(t.copy())

tasks = st.session_state.tasks_by_date[date_str]
total = len(tasks)
done = sum(t.get("completed", False) for t in tasks)
score = int(done / total * 100) if total else 0

# CSS — BEAUTIFUL CLICKABLE BADGE WITH COLOR
st.markdown(f"""
<style>
    .reportview-container {{ background: {bg}; color: {text} }}
    .task-card {{ padding: 20px; margin: 16px 0; border-radius: 20px; background: rgba(255,75,75,0.1);
                  border-left: 8px solid {accent}; box-shadow: 0 8px 25px rgba(0,0,0,0.3); }}
    .task-card.completed {{ opacity: 0.6; text-decoration: line-through; }}
    .progress-fill {{ height: 70px; width: {score}%; background: linear-gradient(90deg, #ff4b4b, #00ff88);
                      border-radius: 35px; display: flex; align-items: center; justify-content: center;
                      font-size: 36px; font-weight: bold; color: white; }}
    .priority-badge button {{
        background: var(--bg-color) !important;
        color: white !important;
        border: none !important;
        border-radius: 50px !important;
        padding: 11px 30px !important;
        font-weight: bold !important;
        font-size: 14px !important;
        box-shadow: 0 6px 18px rgba(0,0,0,0.4) !important;
        transition: all 0.25s ease !important;
        cursor: pointer !important;
    }}
    .priority-badge button:hover {{
        transform: scale(1.18) !important;
        box-shadow: 0 12px 30px rgba(0,0,0,0.5) !important;
    }}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown(f"<h1 style='color:{accent};'>Dojo — {st.session_state.user_name}'s Life OS</h1>", unsafe_allow_html=True)

# Add task
new_task = st.text_input("What needs to be done?", key="add_task", label_visibility="collapsed", placeholder="Type and pick priority →")
if new_task.strip():
    cols = st.columns(4)
    for i, p in enumerate(PRIORITIES):
        with cols[i]:
            if st.button(p, key=f"add_with_{p}", use_container_width=True):
                tasks.append({"text": new_task.strip(), "completed": False, "notes": "", "priority": p})
                del st.session_state["add_task"]
                st.rerun()

# Progress bar
st.markdown(f"<div class='progress-fill'>{score}%</div>", unsafe_allow_html=True)

# Tasks
for i in range(len(tasks)):
    task = tasks[i]
    priority = task.get("priority", "Low")
    color = PRIORITY_COLORS[priority]
    edit_key = f"edit_prio_{date_str}_{i}"

    st.markdown(f"<div class='task-card{' completed' if task.get('completed') else ''}>", unsafe_allow_html=True)

    # RED "Critical" BADGE — FULLY CLICKABLE, FULL COLOR, NO WHITE BOX
    if st.session_state.get(edit_key):
        st.markdown("**Change priority:**")
        cols = st.columns(4)
        for j, np in enumerate(PRIORITIES):
            with cols[j]:
                if st.button(np, key=f"set_prio_{i}_{np}"):
                    tasks[i]["priority"] = np
                    st.session_state[edit_key] = False
                    st.rerun()
        if st.button("Cancel", key=f"cancel_prio_{i}"):
            st.session_state[edit_key] = False
            st.rerun()
    else:
        # THE FINAL WINNING BADGE
        st.markdown(
            f'<div class="priority-badge" style="--bg-color:{color}">'
            f'<button type="button">{priority}</button></div>',
            unsafe_allow_html=True
        )
        col_badge, col_spacer = st.columns([0.2, 0.8])
        with col_badge:
            if st.button("", key=f"click_badge_{i}"):
                st.session_state[edit_key] = True
                st.rerun()

    # Task text
    st.markdown(f"### {task['text']}")

    # Action buttons
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if task.get("completed"):
            st.success("DONE")
        else:
            if st.button("Complete", key=f"complete_{i}"):
                tasks[i]["completed"] = True
                st.rerun()
    with c2:
        if st.button("Notes", key=f"notes_btn_{i}"):
            st.session_state[f"notes_open_{i}"] = True
    with c3:
        if st.button("Edit", key=f"edit_btn_{i}"):
            st.session_state[f"editing_{i}"] = True
    with c4:
        if st.button("Delete", key=f"delete_{i}"):
            tasks.pop(i)
            st.rerun()

    # Notes
    if st.session_state.get(f"notes_open_{i}"):
        note = st.text_area("Note", value=task.get("notes", ""), key=f"note_input_{i}", height=100)
        ca, cb = st.columns(2)
        with ca:
            if st.button("Save Note", key=f"save_note_{i}"):
                tasks[i]["notes"] = note
                st.session_state[f"notes_open_{i}"] = False
                st.rerun()
        with cb:
            if st.button("Cancel", key=f"cancel_note_{i}"):
                st.session_state[f"notes_open_{i}"] = False
                st.rerun()

    # Edit task text
    if st.session_state.get(f"editing_{i}"):
        new_text = st.text_input("Edit task", value=task["text"], key=f"edit_input_{i}")
        ca, cb = st.columns(2)
        with ca:
            if st.button("Save", key=f"save_edit_{i}"):
                tasks[i]["text"] = new_text.strip()
                st.session_state[f"editing_{i}"] = False
                st.rerun()
        with cb:
            if st.button("Cancel", key=f"cancel_edit_{i}"):
                st.session_state[f"editing_{i}"] = False
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.metric("Flow", f"{score}%")
    st.write(f"**Tasks:** {total} · **Done:** {done}")

st.caption("v11.2 — RED BADGE FULL COLOR + FULLY CLICKABLE + Notes fixed · You are unstoppable")
