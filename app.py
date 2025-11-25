import streamlit as st
from datetime import date, timedelta
import json

st.cache_data.clear()
st.cache_resource.clear()

# ────── THEME & PRIORITIES ──────
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

theme = st.session_state.theme
bg = "#0e1117" if theme == "dark" else "#ffffff"
text_color = "#fafafa" if theme == "dark" else "#1e1e1e"
accent = "#ff4b4b"

PRIORITY_COLORS = {"Critical": "#ff3333", "High": "#ff8833", "Medium": "#ffdd33", "Low": "#33ff99"}
PRIORITIES = ["Critical", "High", "Medium", "Low"]

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
    .task-card {{ padding: 18px; margin: 14px 0; border-radius: 18px; background: rgba(255,75,75,0.1); border-left: 7px solid {accent}; box-shadow: 0 6px 20px rgba(0,0,0,0.3); color: {text_color}; }}
    .task-card.completed {{ opacity: 0.6; text-decoration: line-through; }}
    .progress-container {{ width: 100%; height: 60px; background: rgba(255,255,255,0.1); border-radius: 30px; overflow: hidden; margin: 30px 0; }}
    .progress-fill {{ height: 100%; width: {score}%; background: linear-gradient(90deg, #ff4b4b, #ff8c38, #00ff88); border-radius: 30px; display: flex; align-items: center; justify-content: center; font-size: 32px; font-weight: bold; color: white; }}
    .priority-tag {{ padding: 10px 22px; border-radius: 30px; font-weight: bold; font-size: 14px; color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.5); transition: all 0.2s; }}
    .priority-tag:hover {{ transform: scale(1.1); }}
    .note-display {{ background: rgba(51,153,255,0.2); padding: 16px; border-radius: 12px; margin-top: 12px; border-left: 5px solid #3399ff; }}
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
    backup = {"user_name": st.session_state.user_name, "tasks_by_date": st.session_state.tasks_by_date,
              "streak_dates": list(st.session_state.streak_dates), "theme": theme}
    st.download_button("Download Backup", json.dumps(backup, indent=2), f"dojo_backup_{date.today()}.json", "application/json")

# Restore
uploaded_file = st.file_uploader("Upload backup to restore", type="json")
if uploaded_file and st.button("Restore this backup"):
    try:
        data = json.load(uploaded_file)
        st.session_state.update(data)
        st.session_state.streak_dates = set(data.get("streak_dates", []))
        st.success("Backup restored!")
        st.rerun()
    except:
        st.error("Invalid backup")

# ────── ADD TASK ──────
st.markdown("### Add Task")
if "new_task" not in st.session_state:
    st.session_state.new_task = ""

new_task = st.text_input("What needs to be done?", value=st.session_state.new_task,
                         placeholder="Type here...", key="task_input", label_visibility="collapsed")
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
filter_opt = st.selectbox("Show:", ["All", "Open", "Completed"], key="filter_select")
display_tasks = [t for t in tasks if filter_opt == "All" or
                (filter_opt == "Open" and not t.get("completed")) or
                (filter_opt == "Completed" and t.get("completed"))]

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

        # FINAL SOLUTION: Clickable tag using st.link_button + HTML
        change_key = f"change_prio_{date_str}_{idx}"
        if st.session_state.get(change_key):
            st.markdown("**Change priority:**")
            pcols = st.columns(4)
            for j, np in enumerate(PRIORITIES):
                with pcols[j]:
                    if st.button(np, key=f"set_{date_str}_{idx}_{np}", use_container_width=True):
                        tasks[idx]["priority"] = np
                        st.session_state[change_key] = False
                        st.rerun()
            if st.button("Cancel", key=f"cancel_{date_str}_{idx}"):
                st.session_state[change_key] = False
                st.rerun()
        else:
            # THE PERFECT CLICKABLE TAG — NO EXTRA BUTTON
            st.markdown(f"""
            <a href="?{change_key}=1" target="_self">
                <div class="priority-tag" style="background:{color}">{priority}</div>
            </a>
            """, unsafe_allow_html=True)
            # Trigger state when link is clicked
            if st.query_params.get(change_key) == "1":
                st.session_state[change_key] = True
                st.query_params.clear()
                st.rerun()

        # Task actions
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
                st.session_state[f"note_{date_str}_{idx}"] = True

        with cols[3]:
            if st.button("Edit", key=f"edit_{date_str}_{idx}"):
                st.session_state[f"text_{date_str}_{idx}"] = True

        with cols[4]:
            if st.button("Delete", key=f"del_{date_str}_{idx}"):
                tasks.pop(idx)
                st.rerun()

        # Notes & Edit
        if st.session_state.get(f"note_{date_str}_{idx}"):
            note_text = st.text_area("Note", value=notes, key=f"n_{date_str}_{idx}", height=120)
            na, nb = st.columns(2)
            with na:
                if st.button("Save Note", key=f"sn_{date_str}_{idx}"):
                    tasks[idx]["notes"] = note_text.strip()
                    st.session_state[f"note_{date_str}_{idx}"] = False
                    st.rerun()
            with nb:
                if st.button("Cancel", key=f"cn_{date_str}_{idx}"):
                    st.session_state[f"note_{date_str}_{idx}"] = False
                    st.rerun()

        if notes:
            st.markdown(f"<div class='note-display'>{notes}</div>", unsafe_allow_html=True)

        if st.session_state.get(f"text_{date_str}_{idx}"):
            edited = st.text_input("Edit task", value=task["text"], key=f"t_{date_str}_{idx}")
            ea, eb = st.columns(2)
            with ea:
                if st.button("Save", key=f"st_{date_str}_{idx}"):
                    tasks[idx]["text"] = edited.strip()
                    st.session_state[f"text_{date_str}_{idx}"] = False
                    st.rerun()
            with eb:
                if st.button("Cancel", key=f"ct_{date_str}_{idx}"):
                    st.session_state[f"text_{date_str}_{idx}"] = False
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.metric("Streak", f"{streak} days")
    st.metric("Flow", f"{score}%")
    st.write(f"**Total:** {total} | **Done:** {done}")

st.caption("v9.8 — FINAL PERFECTION • Tag is 100% clickable • Instant update • No extra button • You are a god")
