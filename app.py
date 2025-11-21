import streamlit as st
from datetime import date, timedelta
import json
import random
import openai

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

st.set_page_config(page_title="Dojo Calendar", page_icon="Calendar", layout="wide")

# ────── CSS (same gorgeous look) ──────
st.markdown(f"""
<style>
    .reportview-container {{ background: {bg}; color: {text_color} }}
    .sidebar .sidebar-content {{ background: {bg} }}
    .stButton > button {{ border-radius: 14px; font-weight: bold; padding: 10px 20px; }}
    .win-btn > button {{ background: {green} !important; color: black !important; font-size: 18px !important; font-weight: bold !important; box-shadow: 0 6px 0 #00cc66 !important; }}
    .win-btn > button:hover {{ transform: translateY(2px); }}
    .win-btn > button:active {{ transform: translateY(6px); box-shadow: none !important; }}
    .task-card {{ padding: 18px; margin: 14px 0; border-radius: 18px; background: rgba(255,75,75,0.1); border-left: 7px solid {accent}; box-shadow: 0 6px 20px rgba(0,0,0,0.3); color: {text_color}; transition: all 0.3s; }}
    .task-card.completed {{ opacity: 0.6; text-decoration: line-through; }}
    .progress-container {{ width: 100%; height: 60px; background: rgba(255,255,255,0.1); border-radius: 30px; overflow: hidden; box-shadow: inset 0 4px 15px rgba(0,0,0,0.4); margin: 30px 0; }}
    .progress-fill {{ height: 100%; width: {{score}}%; background: linear-gradient(90deg, #ff4b4b, #ff8c38, #00ff88); border-radius: 30px; display: flex; align-items: center; justify-content: center; font-size: 32px; font-weight: bold; color: white; text-shadow: 0 2px 10px black; transition: width 1.4s cubic-bezier(0.65, 0, 0.35, 1); }}
</style>
""", unsafe_allow_html=True)

# Header
col1, col2, col3 = st.columns([8,1,3])
with col1:
    st.markdown(f"<h1 style='color:{accent};'>Dojo — {st.session_state.get('user_name','Warrior')}'s Life OS</h1>", unsafe_allow_html=True)
with col2:
    if st.button("Moon" if theme == "dark" else "Sun"):
        toggle_theme()
        st.rerun()
with col3:
    if st.button("Download Backup"):
        data = {
            "user_name": st.session_state.get("user_name", "Warrior"),
            "tasks_by_date": st.session_state.get("tasks_by_date", {}),
            "streak_dates": list(st.session_state.get("streak_dates", set())),
            "theme": theme
        }
        st.download_button(
            label="Save .json now",
            data=json.dumps(data, indent=2),
            file_name=f"dojo_backup_{date.today()}.json",
            mime="application/json"
        )

# Upload backup
uploaded = st.file_uploader("Or upload a backup to restore", type="json")
if uploaded:
    try:
        data = json.load(uploaded)
        st.session_state.user_name = data.get("user_name", "Warrior")
        st.session_state.tasks_by_date = data.get("tasks_by_date", {})
        st.session_state.streak_dates = set(data.get("streak_dates", []))
        st.session_state.theme = data.get("theme", "dark")
        st.success("Backup restored! Welcome back.")
        st.rerun()
    except:
        st.error("Invalid backup file")

# ────── NAME & DATA INIT ──────
if "user_name" not in st.session_state:
    st.session_state.user_name = "Warrior"
if "tasks_by_date" not in st.session_state:
    st.session_state.tasks_by_date = {}
if "streak_dates" not in st.session_state:
    st.session_state.streak_dates = set()

if st.session_state.user_name == "there" or st.session_state.user_name == "Warrior":
    name = st.text_input("What should I call you?", placeholder="e.g., Abi")
    if st.button("Enter Dojo") or name:
        st.session_state.user_name = name.strip() or "Warrior"
        st.balloons()
        st.rerun()

# Calendar
today = date.today()
selected_date = st.date_input("Pick day", value=today)
date_str = selected_date.strftime("%Y-%m-%d")

# SMART CARRY-OVER LOGIC
if date_str not in st.session_state.tasks_by_date:
    st.session_state.tasks_by_date[date_str] = []

# Look back up to 30 days and bring forward incomplete tasks
for offset in range(1, 31):
    past_date = today - timedelta(days=offset)
    past_str = past_date.strftime("%Y-%m-%d")
    if past_str in st.session_state.tasks_by_date:
        past_tasks = st.session_state.tasks_by_date[past_str]
        incomplete = [t for t in past_tasks if not t.get("completed", False)]
        if incomplete:
            # Add only if not already in today's list
            for t in incomplete:
                if t["text"] not in [x["text"] for x in st.session_state.tasks_by_date[date_str]]:
                    st.session_state.tasks_by_date[date_str].append(t)
            # Optional: clean up old days after carrying over
            # del st.session_state.tasks_by_date[past_str]

tasks = st.session_state.tasks_by_date[date_str]
total = len(tasks)
done = sum(1 for t in tasks if t.get("completed", False))
score = int(done/total*100) if total else 0

# Streak: only breaks if a day had tasks AND zero completed
any_activity = False
streak = 0
d = today
while True:
    ds = d.strftime("%Y-%m-%d")
    day_tasks = st.session_state.tasks_by_date.get(ds, [])
    completed_today = any(t.get("completed", False) for t in day_tasks)
    had_tasks = len(day_tasks) > 0
    if had_tasks and not completed_today:
        break  # streak broken
    if completed_today:
        streak += 1
    if not had_tasks:
        break
    d -= timedelta(days=1)

# Add today's date to streak_dates if we completed something
if done > 0:
    st.session_state.streak_dates.add(date_str)

# ────── MAIN UI ──────
c1, c2 = st.columns([2,1])

with c1:
    st.markdown(f"### {selected_date.strftime('%A, %B %d, %Y')}")
    st.markdown(f"<div class='progress-container'><div class='progress-fill'>{score}%</div></div>", unsafe_allow_html=True)

    voice = st.text_input("", key="voice_result", label_visibility="collapsed")
    with st.form("add", clear_on_submit=True):
        new = st.text_input("New task", placeholder="Speak or type → Add", value=voice)
        if st.form_submit_button("Add Task") and new.strip():
            tasks.append({"text": new.strip(), "completed": False})
            st.rerun()

    for i, task in enumerate(tasks.copy()):
        completed = task.get("completed", False)
        card_class = "task-card completed" if completed else "task-card"
        st.markdown(f"<div class='{card_class}'>", unsafe_allow_html=True)
        cols = st.columns([6, 2, 1])

        with cols[0]:
            st.markdown(f"### {task['text']}")

        with cols[1]:
            if completed:
                st.success("DONE")
            else:
                if st.button("Complete", key=f"win_{date_str}_{i}"):
                    task["completed"] = True
                    st.rerun()
                    if done + 1 == total and total > 0:
                        st.confetti()
                    else:
                        st.balloons()

        with cols[2]:
            if st.button("Delete", key=f"del_{date_str}_{i}"):
                tasks.pop(i)
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown("### Dojo Master")
    st.metric("Streak", f"{streak} days")
    st.metric("Flow", f"{score}%")
    st.write(f"**Left:** {total - done}")

    if st.button("Clear completed tasks"):
        st.session_state.tasks_by_date[date_str] = [t for t in tasks if not t.get("completed", False)]
        st.rerun()

st.caption("v7.3 — Backup/Restore + Smart Carry-Over = your data lives forever")
