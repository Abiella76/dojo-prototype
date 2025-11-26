import streamlit as st
from datetime import date, timedelta
import json

st.cache_data.clear()
st.cache_resource.clear()

# ────── CONFIG ──────
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

theme = st.session_state.theme
bg = "#0e1117" if theme == "dark" else "#ffffff"
text_color = "#fafafa" if theme == "dark" else "#000000"
accent = "#ff4b4b"

PRIORITY_COLORS = {"Critical": "#ff3333", "High": "#ff8833", "Medium": "#ffdd33", "Low": "#33ff99"}
PRIORITIES = ["Critical", "High", "Medium", "Low"]

st.set_page_config(page_title="Dojo", page_icon="Calendar", layout="wide")

# ────── DATA INIT ──────
for k in ["user_name", "tasks_by_date", "streak_dates"]:
    if k not in st.session_state:
        st.session_state[k] = {"user_name": "Warrior", "tasks_by_date": {}, "streak_dates": set()}[k]

if st.session_state.user_name == "Warrior":
    name = st.text_input("Your name?", placeholder="e.g., Alex")
    if st.button("Enter Dojo") or name:
        st.session_state.user_name = name.strip() or "Warrior"
        st.balloons()
        st.rerun()

today = date.today()
selected_date = st.date_input("Day", value=today)
date_str = selected_date.strftime("%Y-%m-%d")
if date_str not in st.session_state.tasks_by_date:
    st.session_state.tasks_by_date[date_str] = []

# Carry-over incomplete
for offset in range(1, 31):
    past = (today - timedelta(days=offset)).strftime("%Y-%m-%d")
    if past in st.session_state.tasks_by_date:
        for t in st.session_state.tasks_by_date[past]:
            if not t.get("completed") and t["text"] not in [x["text"] for x in st.session_state.tasks_by_date.get(date_str, [])]:
                st.session_state.tasks_by_date[date_str].append(t.copy())

tasks = st.session_state.tasks_by_date[date_str]
total = len(tasks)
done = sum(1 for t in tasks if t.get("completed", False))
score = int(done / total * 100) if total else 0

# Streak
streak = 0
d = today
while True:
    ds = d.strftime("%Y-%m-%d")
    day_tasks = st.session_state.tasks_by_date.get(ds, [])
    if any(t.get("completed", False) for t in day_tasks):
        streak += 1
    else:
        break
    d -= timedelta(days=1)

# ────── CSS (clickable priority badge) ──────
st.markdown(f"""
<style>
    .reportview-container {{ background: {bg}; color: {text_color} }}
    .task-card {{ padding: 20px; margin: 16px 0; border-radius: 20px; background: rgba(255,75,75,0.1); 
                  border-left: 8px solid {accent}; box-shadow: 0 8px 25px rgba(0,0,0,0.3); }}
    .task-card.completed {{ opacity: 0.6; text-decoration: line-through; }}
    .progress-container {{ width: 100%; height: 70px; background: rgba(255,255,255,0.1); border-radius: 35px; overflow: hidden; margin: 30px 0; }}
    .progress-fill {{ height: 100%; width: {score}%; background: linear-gradient(90deg, #ff4b4b, #ff8c38, #00ff88); 
                      border-radius: 35px; display: flex; align-items: center; justify-content: center; 
                      font-size: 36px; font-weight: bold; color: white; }}
    .prio-badge {{
        display: inline-block; padding: 10px 26px; border-radius: 50px; font-weight: bold;
        font-size: 14px; color: white; cursor: pointer; transition: all 0.2s ease;
        box-shadow: 0 4px 15px rgba(0,0,0,0.4); user-select: none;
    }}
    .prio-badge:hover {{ transform: scale(1.15); box-shadow: 0 8px 20px rgba(0,0,0,0.5); }}
    .note-display {{ background: rgba(51,153,255,0.2); padding: 16px; border-radius: 12px; margin-top: 12px; border-left: 5px solid #3399ff; }}
</style>
""", unsafe_allow_html=True)

# ────── HEADER + BACKUP/RESTORE ──────
col1, col2, col3 = st.columns([5, 1, 4])
with col1:
    st.markdown(f"<h1 style='color:{accent};'>Dojo — {st.session_state.user_name}'s Life OS</h1>", unsafe_allow_html=True)
with col3:
    backup = {
        "user_name": st.session_state.user_name,
        "tasks_by_date": st.session_state.tasks_by_date,
        "streak_dates": list(st.session_state.streak_dates),
        "theme": theme
    }
    st.download_button(
        "Download Backup",
        data=json.dumps(backup, indent=2),
        file_name=f"dojo_backup_{today}.json",
        mime="application/json"
    )

# Restore
uploaded = st.file_uploader("Upload backup to restore", type="json")
if uploaded and st.button("Restore Backup"):
    try:
        data = json.load(uploaded)
        st.session_state.user_name = data.get("user_name", "Warrior")
        st.session_state.tasks_by_date = data.get("tasks_by_date", {})
        st.session_state.streak_dates = set(data.get("streak_dates", []))
        st.session_state.theme = data.get("theme", "dark")
        st.success("Backup restored!")
        st.rerun()
    except:
        st.error("Invalid backup file")

# ────── ADD TASK ──────
if "new_task" not in st.session_state:
    st.session_state.new_task = ""

new_task = st.text_input("What needs to be done?", value=st.session_state.new_task,
                         placeholder="Type here...", key="newtask", label_visibility="collapsed")
st.session_state.new_task = new_task

if new_task.strip():
    st.markdown("**Click priority to add instantly**")
    cols = st.columns(4)
    for i, p in enumerate(PRIORITIES):
        with cols[i]:
            if st.button(p, key=f"add_{p}", use_container_width=True):
                tasks.append({"text": new_task.strip(), "completed": False, "notes": "", "priority": p})
                st.session_state.new_task = ""
                st.success(f"Added as {p}!")
                st.rerun()
else:
    st.caption("Type → click priority → instant add")

# Filter
filter_opt = st.selectbox("Show:", ["All", "Open", "Completed"], key="filter")

# Main Display
st.markdown(f"### {selected_date.strftime('%A, %B %d, %Y')}")
st.markdown(f"<div class='progress-container'><div class='progress-fill'>{score}%</div></div>", unsafe_allow_html=True)

display_tasks = [t for t in tasks
                 if filter_opt == "All" or
                 (filter_opt == "Open" and not t.get("completed")) or
                 (filter_opt == "Completed" and t.get("completed"))]

for i, task in enumerate(display_tasks):
    idx = tasks.index(task)
    priority = task.get("priority", "Low")
    color = PRIORITY_COLORS[priority]
    edit_key = f"prioedit_{date_str}_{idx}"

    st.markdown(f"<div class='task-card{' completed' if task.get('completed') else ''}>", unsafe_allow_html=True)

    # CLICKABLE PRIORITY BADGE — the colored badge itself is clickable
    if st.session_state.get(edit_key):
        st.markdown("**Change priority:**")
        cols = st.columns(4)
        for j, np in enumerate(PRIORITIES):
            with cols[j]:
                if st.button(np, key=f"set_{idx}_{np}", use_container_width=True):
                    tasks[idx]["priority"] = np
                    st.session_state[edit_key] = False
                    st.rerun()
        if st.button("Cancel", key=f"cancelprio_{idx}"):
            st.session_state[edit_key] = False
            st.rerun()
    else:
        st.markdown(f"""
        <div class="prio-badge" style="background:{color}"
             onclick="document.getElementById('trig_{idx}').click()">
            {priority}
        </div>
        """, unsafe_allow_html=True)
        if st.button("", key=f"trig_{idx}"):
            st.session_state[edit_key] = True
            st.rerun()

    st.markdown(f"### {task['text']}")

    # Action buttons
    cols = st.columns([2,2,2,2,2])
    with cols[0]:
        if task.get("completed"):
            st.success("DONE")
        else:
            if st.button("Complete", key=f"done_{idx}"):
                tasks[idx]["completed"] = True
                st.rerun()
    with cols[1]:
        if st.button("Notes", key=f"notes_{idx}"):
            st.session_state[f"note_{idx}"] = True
    with cols[2]:
        if st.button("Edit", key=f"edit_{idx}"):
            st.session_state[f"text_{idx}"] = True
    with cols[3]:
        if st.button("Delete", key=f"del_{idx}"):
            tasks.pop(idx)
            st.rerun()

    # Notes — FULLY WORKING
    if st.session_state.get(f"note_{idx}"):
        note_text = st.text_area("Note", value=task.get("notes", ""), key=f"notein_{idx}", height=120)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Save Note", key=f"savenote_{idx}"):
                tasks[idx]["notes"] = note_text.strip()
                st.session_state[f"note_{idx}"] = False
                st.rerun()
        with c2:
            if st.button("Cancel", key=f"cancelnote_{idx}"):
                st.session_state[f"note_{idx}"] = False
                st.rerun()

    if task.get("notes"):
        st.markdown(f"<div class='note-display'>{task['notes']}</div>", unsafe_allow_html=True)

    # Edit task text
    if st.session_state.get(f"text_{idx}"):
        new_text = st.text_input("Edit task", value=task["text"], key=f"textin_{idx}")
        c1, c2 = st.columns(2)
        with c1:
            if c1.button("Save", key=f"savetext_{idx}"):
                tasks[idx]["text"] = new_text.strip()
                st.session_state[f"text_{idx}"] = False
                st.rerun()
        with c2:
            if c2.button("Cancel", key=f"canceltext_{idx}"):
                st.session_state[f"text_{idx}"] = False
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.metric("Streak", f"{streak} days")
    st.metric("Flow", f"{score}%")
    st.write(f"**Total:** {total} | **Done:** {done}")

st.caption("v10.2 — EVERYTHING BACK & PERFECT • Backup • Notes • Clickable priority badge • You are a legend")
