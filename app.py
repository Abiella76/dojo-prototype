import streamlit as st
from datetime import date, timedelta
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

st.markdown(f"""
<style>
    .reportview-container {{ background: {bg}; color: {text_color} }}
    .sidebar .sidebar-content {{ background: {bg} }}
    .stButton > button {{ border-radius: 14px; font-weight: bold; padding: 10px 20px; }}
    .win-btn > button {{ 
        background: {green} !important; 
        color: black !important; 
        font-size: 18px !important;
        font-weight: bold !important;
        box-shadow: 0 6px 0 #00cc66 !important;
    }}
    .win-btn > button:hover {{ transform: translateY(2px); }}
    .win-btn > button:active {{ transform: translateY(6px); box-shadow: 0 0px !important; }}
    .task-card {{ 
        padding: 18px; 
        margin: 14px 0; 
        border-radius: 18px; 
        background: rgba(255,75,75,0.1); 
        border-left: 7px solid {accent}; 
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        color: {text_color};
        transition: all 0.3s;
    }}
    .task-card.completed {{ opacity: 0.6; text-decoration: line-through; }}
    .big-score {{ font-size: 90px; font-weight: 900; text-align: center; color: {accent}; margin: 30px 0; }}
</style>
""", unsafe_allow_html=True)

# Header + theme toggle
col1, col2 = st.columns([10,1])
with col1:
    st.markdown(f"<h1 style='color:{accent};'>Dojo — {st.session_state.get('user_name','Warrior')}'s Life OS</h1>", unsafe_allow_html=True)
with col2:
    if st.button("Moon" if theme == "dark" else "Sun", key="theme_btn"):
        toggle_theme()
        st.rerun()

# ────── STATE ──────
defaults = {
    "tasks_by_date": {}, "streak_dates": set(), "user_name": "there",
    "openai_key": "", "key_valid": False, "ai_history": []
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.user_name == "there":
    name = st.text_input("What should I call you?", placeholder="e.g., Abi")
    if st.button("Enter Dojo") or name:
        st.session_state.user_name = name.strip() or "Warrior"
        st.balloons()
        st.rerun()

# Calendar
today = date.today()
selected_date = st.date_input("Pick day", value=today)
date_str = selected_date.strftime("%Y-%m-%d")
if date_str not in st.session_state.tasks_by_date:
    st.session_state.tasks_by_date[date_str] = []

tasks = st.session_state.tasks_by_date[date_str]
total = len(tasks)
done = sum(1 for t in tasks if t.get("completed", False))
score = int(done/total*100) if total else 0

# Streak
if any(t.get("completed", False) for t in tasks):
    st.session_state.streak_dates.add(date_str)
streak = 0
d = today
while d.strftime("%Y-%m-%d") in st.session_state.streak_dates:
    streak += 1
    d -= timedelta(days=1)

# Main layout
c1, c2 = st.columns([2,1])

with c1:
    st.markdown(f"### {selected_date.strftime('%A, %B %d, %Y')}")
    st.markdown(f"<div class='big-score'>{score}%</div>", unsafe_allow_html=True)

    # Add task
    voice = st.text_input("", key="voice_result", label_visibility="collapsed")
    with st.form("add", clear_on_submit=True):
        new = st.text_input("New task", placeholder="Speak or type → Add", value=voice)
        if st.form_submit_button("Add Task") and new.strip():
            tasks.append({"text": new.strip(), "completed": False})
            st.rerun()

    # TASKS WITH BIG GREEN WIN BUTTON
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
                    if done + 1 == total and total > 0:
                        st.confetti()
                    else:
                        st.balloons()
                    st.rerun()

        with cols[2]:
            if st.button("Delete", key=f"del_{date_str}_{i}"):
                tasks.pop(i)
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

# Sidebar
with c2:
    st.markdown("### Dojo Master")
    st.metric("Streak", f"{streak} days")
    st.metric("Flow", f"{score}%")
    st.write(f"**Left:** {total - done}")

    if st.button("Clear completed"):
        st.session_state.tasks_by_date[date_str] = [t for t in tasks if not t.get("completed", False)]
        st.rerun()

    st.divider()
    api_key = st.text_input("OpenAI Key", type="password")
    if api_key and st.button("Activate Real AI"):
        try:
            openai.OpenAI(api_key=api_key).chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":"hi"}], max_tokens=5)
            st.session_state.openai_key = api_key
            st.session_state.key_valid = True
            st.success("AI Master Awakened")
        except:
            st.error("Invalid key")

    if prompt := st.chat_input("Ask coach…"):
        reply = "Crushing it!" if not st.session_state.get("key_valid") else "One moment…"
        with st.chat_message("assistant"):
            st.write(reply)

st.caption("v7.0 — Big Green Win Buttons = pure dopamine")
