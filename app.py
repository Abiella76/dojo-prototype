import streamlit as st
from datetime import date, timedelta
import json

# ────── THEME & COLORS ──────
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

theme = st.session_state.theme
bg = "#0e1117" if theme == "dark" else "#ffffff"
text_color = "#fafafa" if theme == "dark" else "#1e1e1e"
accent = "#ff4b4b"
green = "#00ff88"
blue = "#3399ff"

# Priority colors
PRIORITY_COLORS = {
    "Critical": "#ff3333",
    "High": "#ff8833",
    "Medium": "#ffdd33",
    "Low": "#33ff99"
}

st.set_page_config(page_title="Dojo", page_icon="Calendar", layout="wide")

# ────── DATA INIT ──────
for key in ["user_name", "tasks_by_date", "streak_dates"]:
    if key not in st.session_state:
        st.session_state[key] = {"user_name": "Warrior", "tasks_by_date": {}, "streak_dates": set()}[key]

if st.session_state.user_name == "Warrior":
    name = st.text_input("Your name?", placeholder="e.g., Abi")
    if st.button("Enter Dojo") or name:
        st.session_state.user_name = name.strip() or "Warrior"
        st.balloons()
        st.rerun()

# Calendar + data
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
            if not t.get("completed") and t["text"] not in [x["text"] for x in st.session_state.tasks_by_date[date_str]]:
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
    if len(day_tasks) > 0 and not any(t.get("completed", False) for t in day_tasks):
        break
    if any(t.get("completed", False) for t in day_tasks):
        streak += 1
    else:
        break
    d -= timedelta(days=1)
if done > 0:
    st.session_state.streak_dates.add(date_str)

# ────── CSS ──────
st.markdown(f"""
<style>
    .reportview-container {{ background: {bg}; color: {text_color} }}
    .stButton > button {{ border-radius: 12px; font-weight: bold; padding: 8px 16px; }}
    .win-btn > button {{ background: {green} !important; color: black !important; font-weight: bold; }}
    .task-card {{ padding: 18px; margin: 14px 0; border-radius: 18px; background: rgba(255,75,75,0.1); border-left: 7px solid {accent}; box-shadow: 0 6px 20px rgba(0,0,0,0.3); color: {text_color}; }}
    .task-card.completed {{ opacity: 0.6; text-decoration: line-through; }}
    .progress-container {{ width: 100%; height: 60px; background: rgba(255,255,255,0.1); border-radius: 30px; overflow: hidden; margin: 30px 0; }}
    .progress-fill {{ height: 100%; width: {score}%; background: linear-gradient(90deg, #ff4b4b, #ff8c38, #00ff88); border-radius: 30px; display: flex; align-items: center; justify-content: center; font-size: 32px; font-weight: bold; color: white; transition: width 1.4s cubic-bezier(0.65, 0, 0.35, 1); }}
    .note-display {{ background: rgba(51,153,255,0.2); padding: 16px; border-radius: 12px; margin-top: 12px; border-left: 5px solid {blue}; font-size: 15px; line-height: 1.5; }}
    .priority-tag {{ padding: 4px 10px; border-radius: 20px; font-weight: bold; font-size: 12px; color: white; }}
</style>
""", unsafe_allow_html=True)

# Header
col1, col2, col3 = st.columns([6,1,5])
with col1:
    st.markdown(f"<h1 style='color:{accent};'>Dojo — {st.session_state.user_name}'s Life OS</h1>", unsafe_allow_html=True)
with col2:
    if st.button("Moon" if theme == "dark" else "Sun"):
        toggle_theme()
        st.rerun()
with col3:
    backup = {
        "user_name": st.session_state.user_name,
        "tasks_by_date": st.session_state.tasks_by_date,
        "streak_dates": list(st.session_state.streak_dates),
        "theme": theme
    }
    st.download_button("Download Backup", json.dumps(backup, indent=2), f"dojo_backup_{date.today()}.json", "application/json")

# Restore
uploaded_file = st.file_uploader("Upload backup to restore", type="json")
if uploaded_file is not None:
    if st.button("Restore this backup"):
        try:
            data = json.load(uploaded_file)
            st.session_state.user_name = data.get("user_name", "Warrior")
            st.session_state.tasks_by_date = data.get("tasks_by_date", {})
            st.session_state.streak_dates = set(data.get("streak_dates", []))
            st.session_state.theme = data.get("theme", "dark")
            st.success("Backup restored!")
            st.rerun()
        except:
            st.error("Invalid backup")

# ────── PRIORITY TASK CREATOR (INSTANT ADD) ──────
st.markdown("### New Task")
new_task_text = st.text_input("What needs to be done?", placeholder="Type your task...", key="new_task_input")

priority = st.radio(
    "Priority (select one to add instantly)",
    ["Critical", "High", "Medium", "Low"],
    horizontal=True,
    key="priority_select"
)

# INSTANT ADD ON PRIORITY SELECT
if st.session_state.get("priority_select") and new_task_text.strip():
    if st.session_state.get("last_task_text") != new_task_text.strip() or st.session_state.get("last_priority") != priority:
        tasks.append({
            "text": new_task_text.strip(),
            "completed": False,
            "notes": "",
            "priority": priority
        })
        st.session_state.last_task_text = new_task_text.strip()
        st.session_state.last_priority = priority
        st.success(f"Added as {priority}!")
        st.rerun()

# ────── FILTER ──────
filter_opt = st.selectbox("Show:", ["All", "Open", "Completed"], key="filter_select")

if filter_opt == "Open":
    display_tasks = [t for t in tasks if not t.get("completed", False)]
elif filter_opt == "Completed":
    display_tasks = [t for t in tasks if t.get("completed", False)]
else:
    display_tasks = tasks

# Main UI
c1, c2 = st.columns([2,1])
with c1:
    st.markdown(f"### {selected_date.strftime('%A, %B %d, %Y')}")
    st.markdown(f"<div class='progress-container'><div class='progress-fill'>{score}%</div></div>", unsafe_allow_html=True)

    for i, task in enumerate(display_tasks):
        idx = tasks.index(task)
        completed = task.get("completed", False)
        notes = task.get("notes", "").strip()
        priority = task.get("priority", "Low")
        color = PRIORITY_COLORS[priority]

        st.markdown(f"<div class='task-card{' completed' if completed else ''}>", unsafe_allow_html=True)
        
        # Priority tag
        st.markdown(f"<div class='priority-tag' style='background:{color}; display:inline-block;'>{priority}</div>", unsafe_allow_html=True)
        
        cols = st.columns([5,2,2,2,2])
        with cols[0]:
            st.markdown(f"### {task['text']}")

        with cols[1]:
            if completed:
                st.success("DONE")
            else:
                if st.button("Complete", key=f"win_{date_str}_{idx}"):
                    tasks[idx]["completed"] = True
                    st.rerun()

        with cols[2]:
            if st.button("Notes", key=f"notes_{date_str}_{idx}"):
                st.session_state[f"note_edit_{date_str}_{idx}"] = True

        with cols[3]:
            if st.button("Edit", key=f"edit_{date_str}_{idx}"):
                st.session_state[f"task_edit_{date_str}_{idx}"] = True

        with cols[4]:
            if st.button("Delete", key=f"del_{date_str}_{idx}"):
                tasks.pop(idx)
                st.rerun()

        # Notes
        if st.session_state.get(f"note_edit_{date_str}_{idx}"):
            note_text = st.text_area("Note", value=notes, key=f"note_in_{date_str}_{idx}", height=120)
            ca, cb = st.columns(2)
            with ca:
                if st.button("Save", key=f"save_n_{date_str}_{idx}"):
                    tasks[idx]["notes"] = note_text.strip()
                    st.session_state[f"note_edit_{date_str}_{idx}"] = False
                    st.rerun()
            with cb:
                if st.button("Cancel", key=f"cancel_n_{date_str}_{idx}"):
                    st.session_state[f"note_edit_{date_str}_{idx}"] = False
                    st.rerun()

        if notes:
            st.markdown(f"<div class='note-display'>{notes}</div>", unsafe_allow_html=True)

        # Edit task
        if st.session_state.get(f"task_edit_{date_str}_{idx}"):
            edited = st.text_input("Edit task", value=task["text"], key=f"task_in_{date_str}_{idx}")
            ca, cb = st.columns(2)
            with ca:
                if st.button("Save", key=f"save_t_{date_str}_{idx}"):
                    tasks[idx]["text"] = edited.strip()
                    st.session_state[f"task_edit_{date_str}_{idx}"] = False
                    st.rerun()
            with cb:
                if st.button("Cancel", key=f"cancel_t_{date_str}_{idx}"):
                    st.session_state[f"task_edit_{date_str}_{idx}"] = False
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.metric("Streak", f"{streak} days")
    st.metric("Flow", f"{score}%")
    st.write(f"**Total:** {total} | **Done:** {done}")

st.caption("v9.0 — PRIORITY SYSTEM ADDED • Select priority = instant add • Color-coded glory")
