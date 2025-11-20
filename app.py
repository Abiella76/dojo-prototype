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

st.set_page_config(page_title="Dojo Calendar", page_icon="Calendar", layout="wide")

# ────── CSS ──────
st.markdown(f"""
<style>
    .reportview-container {{ background: {bg}; color: {text_color} }}
    .sidebar .sidebar-content {{ background: {bg} }}
    .stButton>button {{ background: {accent}; color: white; border: none; border-radius: 12px; padding: 10px 20px; }}
    .task-card {{ 
        padding: 16px; 
        margin: 12px 0; 
        border-radius: 16px; 
        background: rgba(255,75,75,0.1); 
        border-left: 6px solid {accent}; 
        box-shadow: 0 4px 20px rgba(0,0,0,0.25);
        color: {text_color} !important;
    }}
    .task-card.completed {{ 
        opacity: 0.7; 
        text-decoration: line-through;
    }}
    .big-score {{ font-size: 80px; font-weight: bold; text-align: center; color: {accent}; margin: 30px 0; }}
    .stCheckbox > label {{ color: {text_color} !important; }}
</style>
""", unsafe_allow_html=True)

# Header + toggle
col1, col2 = st.columns([10,1])
with col1:
    st.markdown(f"<h1 style='color:{accent}; margin:0;'>Dojo Calendar — {st.session_state.get('user_name','Warrior')}'s Life OS</h1>", unsafe_allow_html=True)
with col2:
    if st.button("Moon" if theme == "dark" else "Sun", key="theme_btn"):
        toggle_theme()
        st.rerun()

# ────── SESSION STATE ──────
defaults = {
    "tasks_by_date": {}, "streak_dates": set(), "user_name": "there",
    "openai_key": "", "key_valid": False, "editing_task": None, "ai_history": []
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Name
if st.session_state.user_name == "there":
    name = st.text_input("What should I call you, warrior?", placeholder="e.g., Abi")
    if st.button("Enter the Dojo") or name:
        st.session_state.user_name = name.strip() or "Warrior"
        st.balloons()
        st.rerun()

# Calendar
today = date.today()
selected_date = st.date_input("Choose your day", value=today)
date_str = selected_date.strftime("%Y-%m-%d")
if date_str not in st.session_state.tasks_by_date:
    st.session_state.tasks_by_date[date_str] = []

tasks = st.session_state.tasks_by_date[date_str]
total = len(tasks)
done = sum(1 for t in tasks if t.get("completed"))
score = int(done/total*100) if total else 0

# Streak
if any(t.get("completed") for t in tasks):
    st.session_state.streak_dates.add(date_str)
streak = 0
d = today
while d.strftime("%Y-%m-%d") in st.session_state.streak_dates:
    streak += 1
    d -= timedelta(days=1)

# ────── MAIN AREA ──────
c1, c2 = st.columns([2,1])

with c1:
    st.markdown(f"### {selected_date.strftime('%A, %B %d, %Y')}")
    st.markdown(f"<div class='big-score'>{score}%</div>", unsafe_allow_html=True)

    # Add task
    voice = st.text_input("", key="voice_result", label_visibility="collapsed")
    with st.form("add", clear_on_submit=True):
        new = st.text_input("Add task", placeholder="Speak or type → Add", value=voice)
        if st.form_submit_button("Add") and new.strip():
            tasks.append({"text": new.strip(), "completed": False})
            st.rerun()

    # Tasks — NOW VISIBLE!
    for i, task in enumerate(tasks.copy()):
        completed = task.get("completed", False)
        card_class = "task-card completed" if completed else "task-card"

        st.markdown(f"<div class='{card_class}'>", unsafe_allow_html=True)
        cols = st.columns([5,1,1])

        if st.session_state.editing_task == f"{date_str}_{i}":
            edited = st.text_input("Edit task", value=task["text"], key=f"e_{date_str}_{i}")
            sa, ca = st.columns(2)
            with sa:
                if st.button("Save", key=f"s_{date_str}_{i}"):
                    tasks[i]["text"] = edited.strip()
                    st.session_state.editing_task = None
                    st.rerun()
            with ca:
                if st.button("Cancel", key=f"c_{date_str}_{i}"):
                    st.session_state.editing_task = None
                    st.rerun()
        else:
            with cols[0]:
                # THIS LINE FIXED — no more collapsed label!
                checked = st.checkbox(task["text"], value=completed, key=f"cb_{date_str}_{i}")
                if checked != completed:
                    task["completed"] = checked
                    if checked and score == 100 and total > 0:
                        st.confetti()
                    elif checked:
                        st.balloons()
                    st.rerun()

            with cols[1]:
                if st.button("Edit", key=f"edit_{date_str}_{i}"):
                    st.session_state.editing_task = f"{date_str}_{i}"
                    st.rerun()
            with cols[2]:
                if st.button("Delete", key=f"del_{date_str}_{i}"):
                    tasks.pop(i)
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

# ────── SIDEBAR (cleaned up) ──────
with c2:
    st.markdown("### Dojo Master")
    st.metric("Streak", f"{streak} days")
    st.metric("Flow", f"{score}%")
    st.write(f"**Left:** {total - done}")

    if st.button("Clear completed"):
        st.session_state.tasks_by_date[date_str] = [t for t in tasks if not t.get("completed")]
        st.rerun()

    st.divider()
    api_key = st.text_input("OpenAI Key", type="password")
    if api_key and st.button("Activate AI"):
        try:
            openai.OpenAI(api_key=api_key).chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":"hi"}], max_tokens=5)
            st.session_state.openai_key = api_key
            st.session_state.key_valid = True
            st.success("AI Master Awakened")
        except:
            st.error("Invalid key")

    if prompt := st.chat_input(f"Ask about {selected_date.strftime('%b %d')}…"):
        reply = "You're crushing it!" if not st.session_state.get("key_valid") else "Thinking..."
        with st.chat_message("assistant"):
            st.write(reply)
        st.session_state.ai_history.append({"role": "assistant", "content": reply})

st.caption("Built with love by Grok & you — Task text 100% visible v6.2")
