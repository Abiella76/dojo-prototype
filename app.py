import streamlit as st
from datetime import datetime, timedelta
import random

# ────── FORCE INITIALIZE EVERYTHING SAFELY ──────
if "tasks" not in st.session_state:
    st.session_state.tasks = []                     # [] = {text:"", completed:False}
if "points" not in st.session_state:
    st.session_state.points = 0
if "streak" not in st.session_state:
    st.session_state.streak = 0
if "last_date" not in st.session_state:
    st.session_state.last_date = datetime.now().date()
if "ai_history" not in st.session_state:
    st.session_state.ai_history = []

# ────── MOCK AI RESPONSES (real Grok API coming next) ──────
AI_RESPONSES = [
    "Solid move! That one’s going to feel great when it’s checked off.",
    "Love the balance you’re building. Anything else you want to stack on top?",
    "Pro tip: knock out the hardest one first tomorrow — huge dopamine hit waiting!",
    "You’re on a roll. Let’s keep that streak alive 🔥",
    "Quick sensei nudge: no movement task today — even a 10-min walk counts!",
    "Crushed yesterday! What’s the one thing you’re most pumped to finish tomorrow?"
]

def get_ai_response(prompt, tasks):
    task_text = " ".join(t["text"] for t in tasks).lower()
    if "fit" not in task_text and "walk" not in task_text and "gym" not in task_text:
        return "Sensei noticing… no fitness today? Even a quick stretch keeps the energy high. Want one?"
    return random.choice(AI_RESPONSES)

def end_day_carry_over():
    today = datetime.now().date()
    # only run once per real day
    if st.session_state.last_date != today:
        unfinished = [t for t in st.session_state.tasks if not t.get("completed", False)]
        st.session_state.tasks = unfinished
        # streak logic
        if st.session_state.tasks:          # had something to do
            st.session_state.streak +=  += 1
        else:
            st.session_state.streak = 0
        st.session_state.last_date = today
        st.success("Day closed — unfinished tasks rolled to tomorrow!")
        st.rerun()

# ────── PAGE CONFIG & TITLE ──────
st.set_page_config(page_title="Dojo", page_icon="Dojo", layout="wide")
st.title("Dojo — Your Nightly Productivity Ritual")

# auto carry-over on new day
end_day_carry_over()

# ────── SIDEBAR – AI COACH ──────
with st.sidebar:
    st.header("Dojo Master")
    # show last few messages
    for msg in st.session_state.ai_history[-6:]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

   
