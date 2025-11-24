import streamlit as st
from datetime import date, timedelta
import json

# ────── THEME ──────
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

st.set_page_config(page_title="Dojo", page_icon="Calendar", layout="wide")

st.markdown(f"""
<style>
    .reportview-container {{ background: {bg}; color: {text_color} }}
    .sidebar .sidebar-content {{ background: {bg} }}
    .stButton > button {{ border-radius: 12px; font-weight: bold; padding: 8px 16px; }}
    .win-btn > button {{ background: {green} !important; color: black !important; font-weight: bold; }}
    .note-btn > button {{ background: {blue} !important; color: white !important; }}
    .task-card {{ padding: 18px; margin: 14px 0; border-radius: 18px; background: rgba(255,75,75,0.1); border-left: 7px solid {accent}; box-shadow: 0 6px 20px rgba(0,0,0,0.3); color: {text_color}; }}
    .task-card.completed {{ opacity: 0.6; text-decoration: line-through; }}
    .progress-container {{ width: 100%; height: 60px; background: rgba(255,255,255,0.1); border-radius: 30px; overflow: hidden; margin: 30px 0; }}
    .progress-fill {{ height: 100%; width: {{score}}%; background: linear-gradient(90deg, #ff4b4b, #ff8c38, #00ff88); border-radius: 30px; display: flex; align-items: center; justify-content: center; font-size: 32px; font-weight: bold; color: white; transition: width 1.4s cubic-bezier(0.65, 0, 0.35, 1); }}
    .note-area {{ background: rgba(255,255,255,0.1); padding: 10px; border-radius: 8px; margin-top: 10px; }}
</style>
""", unsafe_allow_html=True)

# Header + Backup
col1, col2, col3 = st.columns([7,1,4])
with col1:
    st.markdown(f"<h1 style='color:{accent};'>Dojo — {st.session_state.get('user_name','Warrior')}'s Life OS</h1>", unsafe_allow_html=True)
with col2:
    if st.button("Moon" if theme == "dark" else "Sun"):
        toggle_theme()
        st.rerun()
with col3:
    # Download backup
    backup_data = {
        "user_name": st.session_state.get("user_name", "Warrior"),
        "tasks_by_date": st.session_state.get("tasks_by_date", {}),
        "streak_dates": list(st.session_state.get("streak_dates", set())),
        "theme": theme
    }
    st.download_button(
        "Download Backup",
        data=json.dumps(backup_data, indent=2),
        file_name=f"dojo_backup_{date.today()}.json",
        mime="application/json"
    )

# Restore
uploaded = st.file_uploader("Upload backup", type="json")
if uploaded:
    try:
        data = json.load(uploaded)
        st.session_state.user_name = data.get("user_name", "Warrior")
        st.session_state.tasks_by_date = data.get("tasks_by_date", {})
        st.session_state.streak_dates = set(data.get("streak_dates", []))
        st.session_state.theme = data.get("theme", "dark")
        st.success("Backup restored!")
        st.rerun()
    except:
        st.error("Invalid file")

# Init data
for key in ["user_name", "tasks_by_date", "streak_dates"]:
    if key not in st.session_state:
        st.session_state[key] = {"user_name": "Warrior", "tasks_by_date": {}, "streak_dates": set()}[key]

if st.session_state.user_name in ["there", "Warrior"] and "user_name" not in st.query_params:
    name = st.text_input("Your name?", placeholder="e.g., Abi")
    if st.button("Enter Dojo") or name:
        st.session_state.user_name = name.strip() or "Warrior"
        st.balloons()
        st.rerun()

# Calendar + Carry-over
today = date.today()
selected_date = st.date_input("Day", value=today)
date_str = selected_date.strftime("%Y-%m-%d")
if date_str not in st.session_state.tasks_by_date:
    st.session_state.tasks_by_date[date_str] = []

# Carry over incomplete tasks from past 30 days
for offset in range(1, 31):
    past = (today - timedelta(days=offset)).strftime("%Y-%m-%d")
    if past in st.session_state.tasks_by_date:
        for t in st.session_state.tasks_by_date[past]:
            if not t.get("completed") and t["text"] not in [x["text"] for x in st.session_state.tasks_by_date[date_str]]:
                st.session_state.tasks_by_date[date_str].append(t.copy())

tasks = st.session_state.tasks_by_date[date_str]
total = len(tasks)
done = sum(1 for t in tasks if t.get("completed", False))
score = int(done/total*100) if total else 0

# Streak logic
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

# Main UI
c1, c2 = st.columns([2,1])
with c1:
    st.markdown(f"### {selected_date.strftime('%A, %B %d, %Y')}")
    st.markdown(f"<div class='progress-container'><div class='progress-fill'>{score}%</div></div>", unsafe_allow_html=True)

    # Add task
    with st.form("add", clear_on_submit=True):
        new = st.text_input("New task", placeholder="Speak or type → Add")
        if st.form_submit_button("Add Task") and new.strip():
            tasks.append({"text": new.strip(), "completed": False, "notes": ""})
            st.rerun()

    # TASKS — 4 buttons!
    for i, task in enumerate(tasks.copy()):
        completed = task.get("completed", False)
        st.markdown(f"<div class='task-card{' completed' if completed else ''}>", unsafe_allow_html=True)

        cols = st.columns([5, 2, 2, 2, 2])

        with cols[0]:
            st.markdown(f"### {task['text']}")

        with cols[1]:
            if completed:
                st.success("DONE")
            else:
                if st.button("Complete", key=f"win_{date_str}_{i}", help="Crush it!"):
                    task["completed"] = True
                    st.rerun()
                    if done + 1 == total:
                        st.confetti()
                    else:
                        st.balloons()

        with cols[2]:
            if st.button("Notes", key=f"note_{date_str}_{i}"):
                st.session_state[f"note_open_{date_str}_{i}"] = True

        with cols[3]:
            if st.button("Edit", key=f"edit_{date_str}_{i}"):
                st.session_state[f"editing_{date_str}_{i}"] = True

        with cols[4]:
            if st.button("Delete", key=f"del_{date_str}_{i}"):
                tasks.pop(i)
                st.rerun()

        # Notes area
        if st.session_state.get(f"note_open_{date_str}_{i}"):
            note = st.text_area("Notes", value=task.get("notes", ""), key=f"notes_input_{date_str}_{i}", height=100)
            col_save, col_close = st.columns(2)
            with col_save:
                if st.button("Save Notes", key=f"save_note_{date_str}_{i}"):
                    task["notes"] = note
                    st.session_state[f"note_open_{date_str}_{i}"] = False
                    st.rerun()
            with col_close:
                if st.button("Close", key=f"close_note_{date_str}_{i}"):
                    st.session_state[f"note_open_{date_str}_{i}"] = False
                    st.rerun()
            if task.get("notes"):
                st.info(task["notes"])

        # Edit mode
        if st.session_state.get(f"editing_{date_str}_{i}"):
            edited = st.text_input("Edit task", value=task["text"], key=f"edit_input_{date_str}_{i}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Save", key=f"save_edit_{date_str}_{i}"):
                    task["text"] = edited.strip()
                    st.session_state[f"editing_{date_str}_{i}"] = False
                    st.rerun()
            with c2:
                if st.button("Cancel", key=f"cancel_edit_{date_str}_{i}"):
                    st.session_state[f"editing_{date_str}_{i}"] = False
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.metric("Streak", f"{streak} days")
    st.metric("Flow", f"{score}%")
    st.write(f"**Left:** {total - done}")
    if st.button("Clear completed"):
        st.session_state.tasks_by_date[date_str] = [t for t in tasks if not t.get("completed", False)]
        st.rerun()

st.caption("v7.4 — Edit is back + Notes button + 4-button glory")
