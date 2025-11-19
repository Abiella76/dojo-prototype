import streamlit as st
from datetime import datetime, timedelta
import random

# ────── FORCE INITIALIZE EVERYTHING SAFELY ──────
if "tasks" not in st.session_state:
    st.session_state.tasks = []
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
    if st.session_state.last_date != today:
        unfinished = [t for t in st.session_state.tasks if not t.get("completed", False)]
        st.session_state.tasks = unfinished
        if st.session_state.tasks:  # had something to do
            st.session_state.streak += 1
        else:
            st.session_state.streak = 0
        st.session_state.last_date = today
        st.success("Day closed — unfinished tasks rolled to tomorrow!")
        st.rerun()

# ────── PAGE CONFIG & TITLE ──────
st.set_page_config(page_title="Dojo", page_icon="🥋", layout="wide")
st.title("🥋 Dojo: Your Nightly Productivity Ritual")

# auto carry-over on new day
end_day_carry_over()

# ────── SIDEBAR – AI COACH ──────
with st.sidebar:
    st.header("🤖 Your AI Dojo Master")
    for msg in st.session_state.ai_history[-6:]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Chat with your coach… (e.g., 'Suggest a task')"):
        st.session_state.ai_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        reply = get_ai_response(prompt, st.session_state.tasks)
        st.session_state.ai_history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.write(reply)
        st.rerun()

    st.divider()
    st.metric("Total Points", st.session_state.points)
    st.metric("Current Streak", f"{st.session_state.streak} days")

# ────── MAIN AREA ──────
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader(f"📋 Tomorrow's Dojo — {datetime.now().date() + timedelta(days=1):%b %d, %Y}")

    with st.form("add_task_form", clear_on_submit=True):
        new_task = st.text_input("New task", placeholder="e.g. Call mom, 30 min run, Finish slides")
        if st.form_submit_button("Add Task"):
            if new_task.strip():
                st.session_state.tasks.append({"text": new_task.strip(), "completed": False})
                st.success(f"Added: {new_task}")
                st.rerun()

    # Tasks list
    completed_count = sum(1 for t in st.session_state.tasks if t.get("completed", False))
    total_count = len(st.session_state.tasks)
    score = int((completed_count / total_count * 100) if total_count else 0)
    st.metric("Today's Score", f"{score}%")

    for i, task in enumerate(st.session_state.tasks.copy()):
        cols = st.columns([4, 1, 1])
        with cols[0]:
            if st.checkbox(task["text"], value=task.get("completed", False), key=f"cb_{i}"):
                if not task.get("completed", False):
                    task["completed"] = True
                    st.session_state.points += 10
                    st.balloons()
                    st.rerun()
        with cols[1]:
            if st.button("✓", key=f"check_{i}", disabled=task.get("completed", False)):
                task["completed"] = True
                st.session_state.points += 10
                st.balloons()
                st.rerun()
        with cols[2]:
            if st.button("🗑️", key=f"del_{i}"):
                st.session_state.tasks.pop(i)
                st.rerun()

with c2:
    st.subheader("Quick Stats")
    st.write(f"**Left:** {total_count - completed_count}")
    if st.button("End Day & Carry Over", type="primary", use_container_width=True):
        end_day_carry_over()

    if st.button("Reset Streak (for testing)"):
        st.session_state.streak = 0
        st.rerun()

    st.caption("Built with ❤️ by Grok & Abi")

# ────── DONE ──────
