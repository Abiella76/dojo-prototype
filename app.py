import streamlit as st
from datetime import date, timedelta
import json

# Force fresh deploy
st.cache_data.clear()
st.cache_resource.clear()

# ────── THEME & PRIORITY COLORS ──────
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

PRIORITY_COLORS = {
    "Critical": "#ff3333",
    "High": "#ff8833",
    "Medium": "#ffdd33",
    "Low": "#33ff99"
}

PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}

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

# ────── CSS ──────
st.markdown(f"""
<style>
    .reportview-container {{ background: {bg}; color: {text_color} }}
    .stButton > button {{ border-radius: 12px; font-weight: bold; padding: 8px 16px; }}
    .task-card {{ padding: 18px; margin: 14px 0; border-radius: 18px; background: rgba(255,75,75,0.1); border-left: 7px solid {accent}; box-shadow: 0 6px 20px rgba(0,0,0,0.3); color: {text_color}; }}
    .task-card.completed {{ opacity: 0.6; text-decoration: line-through; }}
    .progress-container {{ width: 100%; height: 60px; background: rgba(255,255,255,0.1); border-radius: 30px; overflow: hidden; margin: 30px 0; }}
    .progress-fill {{ height: 100%; width: {score}%; background: linear-gradient(90deg, #ff4b4b, #ff8c38, #00ff88); border-radius: 30px; display: flex; align-items: center; justify-content: center; font-size: 32px; font-weight: bold; color: white; transition: width 1.4s cubic-bezier(0.65, 0, 0.35, 1); }}
    .priority-tag {{ 
        padding: 7px 16px; border-radius: 30px; font-weight: bold; font-size: 14px; 
        color: white; display: inline-block; margin-bottom: 12px;
        cursor: pointer; transition: all 0.2s;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }}
    .priority-tag:hover {{ transform: scale(1.05); }}
    .note-display {{ background: rgba(51,153,255,0.2); padding: 16px; border-radius: 12px; margin-top: 12px; border-left: 5px solid {blue}; }}
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
    backup = {k: v if k != "streak_dates" else list(v) for k, v in st.session_state.items() if k in ["user_name","tasks_by_date","streak_dates","theme"]}
    backup["theme"] = theme
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

# ────── ADD TASK WITH PRIORITY BUTTONS ──────
st.markdown("### Add Task")
if "new_task" not in st.session_state:
    st.session_state.new_task = ""

new_task = st.text_input(
    "What needs to be done?",
    value=st.session_state.new_task,
    placeholder="Type here...",
    key="task_input",
    label_visibility="collapsed"
)
st.session_state.new_task = new_task

if new_task.strip():
    st.markdown("**Click priority to add instantly**")
    cols = st.columns(4)
    for i, p in enumerate(["Critical", "High", "Medium", "Low"]):
        with cols[i]:
            if st.button(p, key=f"new_{p}", use_container_width=True):
                tasks.append({"text": new_task.strip(), "completed": False, "notes": "", "priority": p})
                st.session_state.new_task = ""
                st.success(f"Added as {p}!")
                st.rerun()
else:
    st.caption("Type → pick priority → instant add")

# ────── FILTER ──────
filter_opt = st.selectbox("Show:", ["All", "Open", "Completed"], key="filter_select")
display_tasks = tasks if filter_opt == "All" else \
                [t for t in tasks if not t.get("completed", False)] if filter_opt == "Open" else \
                [t for t in tasks if t.get("completed", False)]

# Main UI
c1, c2 = st.columns([2,1])
with c1:
    st.markdown(f"### {selected_date.strftime('%A, %B %d, %Y')}")
    st.markdown(f"<div class='progress-container'><div class='progress-fill'>{score}%</div></div>", unsafe_allow_html=True)

    for i, task in enumerate(display_tasks):
        idx = tasks.index(task)
        completed = task.get("completed", False)
        notes = task.get("notes", "").strip()
        current_priority = task.get("priority", "Low")
        color = PRIORITY_COLORS[current_priority]

        st.markdown(f"<div class='task-card{' completed' if completed else ''}>", unsafe_allow_html=True)

        # CLICKABLE PRIORITY TAG
        if st.button(current_priority, key=f"tag_{date_str}_{idx}", help="Click to change priority"):
            st.session_state[f"changing_priority_{date_str}_{idx}"] = True

        st.markdown(f"<div class='priority-tag' style='background:{color}'>{current_priority}</div>", unsafe_allow_html=True)

        # CHANGE PRIORITY INLINE
        if st.session_state.get(f"changing_priority_{date_str}_{idx}"):
            st.markdown("**Change priority:**")
            pcols = st.columns(4)
            for j, new_p in enumerate(["Critical", "High", "High", "Medium", "Low"]):
                with pcols[j]:
                    if st.button(new_p, key=f"set_p_{date_str}_{idx}_{new_p}", use_container_width=True):
                        tasks[idx]["priority"] = new_p
                        st.session_state[f"changing_priority_{date_str}_{idx}"] = False
                        st.success(f"Priority → {new_p}")
                        st.rerun()
            if st.button("Cancel", key=f"cancel_p_{date_str}_{idx}"):
                st.session_state[f"changing_priority_{date_str}_{idx}"] = False
                st.rerun()

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
            na, nb = st.columns(2)
            with na:
                if st.button("Save Note", key=f"save_n_{date_str}_{idx}"):
                    tasks[idx]["notes"] = note_text.strip()
                    st.session_state[f"note_edit_{date_str}_{idx}"] = False
                    st.rerun()
            with nb:
                if st.button("Cancel", key=f"cancel_n_{date_str}_{idx}"):
                    st.session_state[f"note_edit_{date_str}_{idx}"] = False
                    st.rerun()

        if notes:
            st.markdown(f"<div class='note-display'>{notes}</div>", unsafe_allow_html=True)

        # Edit task text
        if st.session_state.get(f"task_edit_{date_str}_{idx}"):
            edited = st.text_input("Edit task", value=task["text"], key=f"task_in_{date_str}_{idx}")
            ea, eb = st.columns(2)
            with ea:
                if st.button("Save", key=f"save_t_{date_str}_{idx}"):
                    tasks[idx]["text"] = edited.strip()
                    st.session_state[f"task_edit_{date_str}_{idx}"] = False
                    st.rerun()
            with eb:
                if st.button("Cancel", key=f"cancel_t_{date_str}_{idx}"):
                    st.session_state[f"task_edit_{date_str}_{idx}"] = False
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.metric("Streak", f"{streak} days")
    st.metric("Flow", f"{score}%")
    st.write(f"**Total:** {total} | **Done:** {done}")

st.caption("v9.4 — Click priority tag to change it • Instant add • You are operating at peak human performance")
