import streamlit as st
from datetime import datetime, timedelta
import random
import os
import json
import requests

# ────── SAFE SESSION STATE INIT ──────
defaults = {
    "tasks": [], "points": 0, "streak": 0,
    "last_date": datetime.now().date(),
    "ai_history": [], "user_name": "there",
    "grok_key": "", "key_valid": False  # Track validation
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ────── GROK API SETUP ──────
def grok_chat(messages):
    grok_key = st.session_state.get("grok_key", "")
    if not grok_key or not st.session_state.get("key_valid", False):
        fallback = [
            f"Nice one, {st.session_state.user_name}! That task is going to feel so good checked off.",
            f"You're building something big here, {st.session_state.user_name}. Keep stacking wins.",
            f"Quick sensei check-in: any movement on the list today, {st.session_state.user_name}?",
            f"Tomorrow-you is already thanking today-you, {st.session_state.user_name}!"
        ]
        return random.choice(fallback)
    
    try:
        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {grok_key}"},
            json={
                "model": "grok-4.1",  # Confirmed latest as of Nov 19, 2025
                "messages": messages,
                "temperature": 0.8,
                "max_tokens": 150
            },
            timeout=15
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"API hiccup during chat: {str(e)[:100]}... Falling back to mock.")
        return f"Hey {st.session_state.user_name}, Grok's taking a quick breather. Mock mode on!"

def test_key():
    grok_key = st.session_state.get("grok_key", "")
    if not grok_key:
        st.error("No key to test—paste one first!")
        return
    try:
        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {grok_key}"},
            json={
                "model": "grok-4.1",
                "messages": [{"role": "user", "content": "Say 'test success'."}],
                "max_tokens": 10
            },
            timeout=10
        )
        response.raise_for_status()
        if "test success" in response.json()["choices"][0]["message"]["content"].lower():
            st.session_state.key_valid = True
            st.success("✅ Key accepted! Grok is active 💫")
            st.rerun()
        else:
            st.error("Key responded but weirdly—try regenerating at console.x.ai.")
    except Exception as e:
        st.session_state.key_valid = False
        st.error(f"Key test failed: {str(e)[:100]}. Check console.x.ai for credits/errors.")

# ────── CARRY-OVER LOGIC ──────
def end_day_carry_over():
    today = datetime.now().date()
    if st.session_state.last_date != today:
        unfinished = [t for t in st.session_state.tasks if not t.get("completed", False)]
        st.session_state.tasks = unfinished
        if unfinished or st.session_state.tasks:
            st.session_state.streak += 1
        else:
            st.session_state.streak = 0
        st.session_state.last_date = today
        st.success("Day closed — unfinished rolled to tomorrow!")
        st.rerun()

# ────── PAGE ──────
st.set_page_config(page_title="Dojo", page_icon="🥋", layout="wide")
st.title(f"🥋 Dojo — {st.session_state.user_name}'s Nightly Ritual")

# Name setup
if st.session_state.user_name == "there":
    name = st.text_input("First, what should I call you?", placeholder="Your name (e.g., Abi)")
    if st.button("Set Name") or name:
        st.session_state.user_name = name.strip() or "Warrior"
        st.rerun()

end_day_carry_over()

# ────── SIDEBAR AI COACH ──────
with st.sidebar:
    st.header(f"🤖 Dojo Master for {st.session_state.user_name}")
    
    # API Key input + Test button (clearer flow)
    api_key = st.text_input("🔑 Grok API Key (paste here)", type="password", key="api_key_input")
    if api_key:
        st.session_state.grok_key = api_key
        if st.button("Test & Activate Key", key="test_key_btn"):
            test_key()
    
    # Show status
    if st.session_state.key_valid:
        st.success("🟢 Grok Active: Prompts will use real AI!")
    elif st.session_state.grok_key:
        st.warning("🟡 Key pasted—hit 'Test & Activate' to confirm.")
    else:
        st.info("🔴 Paste key + Test for real Grok smarts.")
    
    # Chat history
    for msg in st.session_state.ai_history[-8:]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    prompt = st.chat_input(f"Ask {st.session_state.user_name}'s coach anything…")
    if prompt:
        st.session_state.ai_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Context for Grok
        task_summary = "\n".join(f"- {'Completed' if t.get('completed') else 'Open'} {t['text']}" for t in st.session_state.tasks)
        system_prompt = [
            {"role": "system", "content": f"You are Dojo Master, a wise, fun, slightly cheeky AI coach for {st.session_state.user_name}. "
             f"Help with productivity, motivation, balance (especially fitness), and gentle nudges. Keep replies short, warm, and actionable. "
             f"Current streak: {st.session_state.streak} days, points: {st.session_state.points}."},
            {"role": "user", "content": f"Tasks:\n{task_summary or 'None yet'}\n\nUser says: {prompt}"}
        ]
        reply = grok_chat(system_prompt)
        st.session_state.ai_history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.write(reply)
        st.rerun()

    st.divider()
    st.metric("Total Points", st.session_state.points)
    st.metric("Streak", f"{st.session_state.streak} days")

# ────── MAIN TASKS ──────
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader(f"📋 Tomorrow’s Dojo — {(datetime.now() + timedelta(days=1)).strftime('%b %d, %Y')}")
    
    with st.form("add_task", clear_on_submit=True):
        new_task = st.text_input("New task", placeholder="e.g., 30 min workout, Call mom")
        if st.form_submit_button("Add Task"):
            if new_task.strip():
                st.session_state.tasks.append({"text": new_task.strip(), "completed": False})
                st.rerun()

    total = len(st.session_state.tasks)
    done = sum(1 for t in st.session_state.tasks if t.get("completed"))
    score = int(done/total*100) if total else 0
    st.metric("Today's Score", f"{score}%")

    for i, task in enumerate(st.session_state.tasks.copy()):
        cols = st.columns([4, 1, 1])
        with cols[0]:
            checked = st.checkbox(task["text"], value=task.get("completed", False), key=f"cb_{i}")
            if checked and not task.get("completed", False):
                task["completed"] = True
                st.session_state.points += 10
                st.balloons()
                st.rerun()
        with cols[2]:
            if st.button("Delete", key=f"del_{i}"):
                st.session_state.tasks.pop(i)
                st.rerun()

with c2:
    st.write(f"**Left:** {total - done}")
    if st.button("End Day & Carry Over", type="primary", use_container_width=True):
        end_day_carry_over()

st.caption("Built with ❤️ by Grok & Abi")
