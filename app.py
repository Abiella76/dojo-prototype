import streamlit as st
from datetime import datetime, timedelta
import random
import os

# ────── SAFE SESSION STATE INIT ──────
defaults = {
    "tasks": [], "points": 0, "streak": 0,
    "last_date": datetime.now().date(),
    "ai_history": [], "user_name": "there"
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ────── GROK API SETUP (real intelligence!) ──────
GROK_API_KEY = st.secrets.get("GROK_API_KEY") or os.getenv("GROK_API_KEY")
if st.sidebar.text_input("🔑 Grok API Key (optional for now)", type="password", value=""):
    st.session_state.grok_key = st.text_input("🔑 Grok API Key", type="password", value="")[0]
elif "grok_key" in st.session_state:
    GROK_API_KEY = st.session_state.grok_key

def grok_chat(messages):
    if not GROK_API_KEY:
        # fallback mock responses
        fallback = [
            f"Nice one, {st.session_state.user_name}! That task is going to feel so good checked off.",
            f"You're building something big here, {st.session_state.user_name}. Keep stacking wins.",
            f"Quick sensei check-in: any movement on the list today, {st.session_state.user_name}?",
            f"Tomorrow-you is already thanking today-you, {st.session_state.user_name} 🔥"
        ]
        return random.choice(fallback)
    
    import requests
    try:
        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROK_API_KEY}"},
            json={
                "model": "grok-beta",
                "messages": messages,
                "temperature": 0.8,
                "max_tokens": 150
            },
            timeout=15
        )
        return response.json()["choices"][0]["message"]["content"]
    except:
        return f"Hey {st.session_state.user_name}, looks like Grok took a quick nap. Try again in a sec!"

# ────── CARRY-OVER LOGIC ──────
def end_day_carry_over():
    today = datetime.now().date()
    if st.session_state.last_date != today:
        unfinished = [t for t in st.session_state.tasks if not t.get("completed", False)]
        st.session_state.tasks = unfinished
        st.session_state.streak = st.session_state.streak + 1 if unfinished or st.session_state.tasks else 0
        st.session_state.last_date = today
        st.success("Day closed — unfinished rolled to tomorrow!")
        st.rerun()

# ────── PAGE ──────
st.set_page_config(page_title="Dojo", page_icon="Dojo", layout="wide")
st.title(f"🥋 Dojo — {st.session_state.user_name}'s Nightly Ritual")

# Ask name once
if st.session_state.user_name == "there":
    name = st.text_input("First, what should I call you?", placeholder="Your name")
    if name:
        st.session_state.user_name = name.strip() or "Warrior"
        st.rerun()

end_day_carry_over()

# ────── SIDEBAR AI COACH (now powered by real Grok!) ──────
with st.sidebar:
    st.header(f"🤖 Dojo Master for {st.session_state.user_name}")
    
    # chat history
    for msg in st.session_state.ai_history[-8:]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    prompt = st.chat_input(f"Ask {st.session_state.user_name}'s coach anything…")
    if prompt:
        st.session_state.ai_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)

        # Build context for Grok
        task_summary = "\n".join(f"- {'✅' if t.get('completed') else '⭕'} {t['text']}" for t in st.session_state.tasks)
        system_prompt = [
            {"role": "system", "content": f"You are Dojo Master, a wise, fun, slightly cheeky AI coach for {st.session_state.user_name}. "
             "You help with productivity, motivation, balance (especially fitness), and gentle nudges. Keep replies short, warm, and actionable."},
            {"role": "user", "content": f"Current tasks:\n{task_summary or 'none yet'}\n\nUser says: {prompt}"}
        ]
        reply = grok_chat(system_prompt)
        st.session_state.ai_history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"): st.write(reply)
        st.rerun()

    st.divider()
    st.metric("Total Points", st.session_state.points)
    st.metric("Streak", f"{st.session_state.streak} days 🔥")

# ────── MAIN TASKS ──────
c1, c2 = st.columns([2,1])

with c1:
    st.subheader(f"Tomorrow’s Dojo — {(datetime.now()+timedelta(days=1)).strftime('%b %d')}")
    
    with st.form("add", clear_on_submit=True):
        new = st.text_input("New task", placeholder="e.g., 30 min workout, Call mom")
        if st.form_submit_button("Add Task"):
            if new.strip():
                st.session_state.tasks.append({"text": new.strip(), "completed": False})
                st.rerun()

    completed = sum(1 for t in st.session_state.tasks if t.get("completed"))
    score = int(completed/len(st.session_state.tasks)*100) if st.session_state.tasks else 0
    st.metric("Score", f"{score}%")

    for i, task in enumerate(st.session_state.tasks.copy()):
        cols = st.columns([4,1,1])
        with cols[0]:
            if st.checkbox
