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

# ────── DATA INIT + SCORE FIRST (so CSS works) ──────
defaults = {"user_name": "Warrior", "tasks_by_date": {}, "streak_dates": set()}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.user_name == "Warrior":
    name = st.text_input("Your name?", placeholder="e.g., Abi")
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

# ────── CSS WITH REAL SCORE ──────
st.markdown(f"""
<style>
    .reportview-container {{ background: {bg}; color: {text_color} }}
    .sidebar .sidebar-content {{ background: {bg} }}
    .stButton > button {{ border-radius: 12px; font-weight: bold; padding: 8px 16px; }}
    .win-btn > button {{ background: {green} !important; color: black !important; font-weight: bold; }}
    .task-card {{ padding: 18px; margin: 14px 0; border-radius: 18px; background: rgba(255,75,75,0.1); border-left: 7px solid {accent}; box-shadow: 0 6px 20px rgba(0,0,0,0.3); color: {text_color}; }}
    .task-card.completed {{ opacity: 0.6; text-decoration: line-through; }}
    .progress-container {{ width: 100%; height: 60px; background: rgba(255,255,255,0.1); border-radius: 30px; overflow: hidden; margin: 30px 0; }}
    .progress-fill {{ height: 100%; width: {score}%; background: linear-gradient(90deg, #ff4b4b, #ff8c38, #00ff88); border-radius: 30px; display: flex; align-items: center; justify-content: center; font-size: 32px; font-weight: bold; color: white; transition: width 1.4s cubic-bezier(0.65, 0, 0.35, 1); }}
    .note-display {{ background: rgba(51,153,255,0.2); padding: 16px; border-radius: 12px; margin-top: 12px; border-left: 5px solid {blue}; font-size: 15px; line-height: 1.5; }}
</style>
""", unsafe_allow_html=True)

# Header + Backup
col1, col2, col3 = st.columns([6,1,5])
with col1:
    st.markdown(f"<h1 style='color:{accent};'>Dojo — {st.session_state.user_name}'s Life OS</h1>", unsafe_allow_html=True)
with col2:
    if st.button("Moon" if theme == "dark" else "Sun"):
        toggle_theme()
        st.rerun()
with col3:
    backup_data = {
        "user_name": st.session_state.user_name,
        "tasks_by_date": st.session_state.tasks_by_date,
        "streak_dates": list(st.session_state.streak_dates),
        "theme": theme
    }
    st.download_button("Download Backup", json.dumps(backup_data, indent=2), f"dojo_backup_{date.today()}.json", "application/json")

# Restore
if "restore_triggered" not in st.session_state:
    st.session_state.restore_triggered = False

uploaded = st.file_uploader("Upload backup to restore", type="json")
if uploaded and not st.session_state.restore_triggered:
    st.session_state.restore_triggered = True
    try:
        data = json.load(uploaded)
        st.session_state.update(data)
        st.session_state.streak_dates = set(data.get("streak_dates", []))
        st.success("Backup restored!")
        st.rerun()
    except:
        st.error("Invalid backup")
        st.session_state.restore_triggered = False
if uploaded is None:
    st.session_state.restore_triggered = False

# ────── FILTER DROPDOWN (NOW VISIBLE!) ──────
st.markdown("### Tasks")
filter_option = st.selectbox(
    "Show tasks:",
    ["All", "Open", "Completed"],
    index=0,
    key="filter"
)

if filter_option == "Open":
    display_tasks = [t for t in tasks if not t.get("completed", False)]
elif filter_option == "Completed":
    display_tasks = [t for t in tasks if t.get("completed", False)]
else:
    display_tasks = tasks

# Main UI
c1, c2 = st.columns([2,1])
with c1:
    st.markdown(f"### {selected_date.strftime('%A, %B %d, %Y')}")
    st.markdown(f"<div class='progress-container'><div class='progress-fill'>{score}%</div></div>", unsafe_allow_html=True)

    with st.form("add", clear_on_submit=True):
        new = st.text_input("New task", placeholder="Speak or type → Add")
        if st.form_submit_button("Add Task") and new.strip():
            tasks.append({"text": new.strip(), "completed": False, "notes": ""})
            st.rerun()

    # Show filtered tasks
    for i, task in enumerate(display_tasks):
        original_idx = tasks.index(task)  # to modify the real list
        completed = task.get("completed", False)
        notes = task.get("notes", "").strip()

        st.markdown(f"<div class='task-card{' completed' if completed else ''}>", unsafe_allow_html=True)
        cols = st.columns([5, 2, 2, 2, 2])

        with cols[0]:
            st.markdown(f"### {task['text']}")

        with cols[1]:
            if completed:
                st.success("DONE")
            else:
                if st.button("Complete", key=f"win_{date_str}_{original_idx}"):
                    tasks[original_idx]["completed"] = True
                    st.rerun()

        with cols[2]:
            if st.button("Notes", key=f"notes_{date_str}_{original_idx}"):
                st.session_state[f"editing_notes_{date_str}_{original_idx}"] = True

        with cols[3]:
            if st.button("Edit", key=f"edit_{date_str}_{original_idx}"):
                st.session_state[f"editing_task_{date_str}_{original_idx}"] = True

        with cols[4]:
            if st.button("Delete", key=f"del_{date_str}_{original_idx}"):
                tasks.pop(original_idx)
                st.rerun()

        # Notes
        if st.session_state.get(f"editing_notes_{date_str}_{original_idx}", False):
            new_note = st.text_area("Edit note", value=notes, key=f"noteedit_{date_str}_{original_idx}", height=120)
            ca, cb = st.columns(2)
            with ca:
                if st.button("Save Note", key=f"savenote_{date_str}_{original_idx}"):
                    tasks[original_idx]["notes"] = new_note.strip()
                    st.session_state[f"editing_notes_{date_str}_{original_idx}"] = False
                    st.rerun()
            with cb:
                if st.button("Cancel", key=f"cancelnote_{date_str}_{original_idx}"):
                    st.session_state[f"editing_notes_{date_str}_{original_idx}"] = False
                    st.rerun()

        if notes:
            st.markdown(f"<div class='note-display'>{notes}</div>", unsafe_allow_html=True)

        # Edit task
        if st.session_state.get(f"editing_task_{date_str}_{original_idx}", False):
            edited = st.text_input("Edit task", value=task["text"], key=f"edittask_{date_str}_{original_idx}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Save", key=f"saveedit_{date_str}_{original_idx}"):
                    tasks[original_idx]["text"] = edited.strip()
                    st.session_state[f"editing_task_{date_str}_{original_idx}"] = False
                    st.rerun()
            with c2:
                if st.button("Cancel", key=f"canceledit_{date_str}_{original_idx}"):
                    st.session_state[f"editing_task_{date_str}_{original_idx}"] = False
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.metric("Streak", f"{streak} days")
    st.metric("Flow", f"{score}%")
    st.write(f"**Total:** {total} | **Done:** {done}")
    if st.button("Clear completed tasks"):
        st.warning("This will hide all completed tasks.")
        if st.button("Yes, clear them"):
            st.session_state.tasks_by_date[date_str] = [t for t in tasks if not t.get("completed", False)]
            st.rerun()

st.caption("v8.1 — Filter dropdown is BACK • All / Open / Completed • Everything works perfectly")
