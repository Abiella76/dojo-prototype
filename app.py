import streamlit as st
from datetime import datetime, timedelta
import random
import json
import requests

# ────── SAFE SESSION STATE INIT ──────
defaults = {
    "tasks": [], "points": 0, "streak": 0,
    "last_date": datetime.now().date(),
    "ai_history": [], "user_name": "there",
    "openai_key": "", "key_valid": False
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ────── OPENAI CHAT (GPT-4o-mini) ──────
def ai_chat(messages):
    key = st.session_state.get("openai_key", "")
    if not key or not st.session_state.get("key_valid", False):
        fallbacks = [
            f"Strong move, {st.session_state.user_name}! That one’s going to feel amazing checked off.",
            f"You’re stacking wins like a pro, {st.session_state.user_name}. Keep the streak alive 🔥",
            f"Quick nudge: any movement on the list today, {st.session_state.user_name}?",
            f"Tomorrow-you is already thanking you, {st.session_state.user_name}!"
        ]
        return random.choice(fallbacks)

    try:
        import openai
        client = openai.OpenAI(api_key=key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",          # Fast, cheap, super smart
            messages=messages,
            temperature=0.8,
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"OpenAI hiccup: {str(e)[:100]}… falling back to mock.")
        return f"Hey {st.session_state.user_name}, coach is warming up. Mock mode on!"

# Test key function
def test_openai_key():
    key = st.session_state.get("openai_key", "")
    if not key:
        st.error("Paste a key first!")
        return
    try:
        import openai
        client = openai.OpenAI(api_key=key)
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'test ok'"}],
            max_tokens=10
        )
        st.session_state.key_valid = True
        st.success("OpenAI key accepted! Real AI coach active")
        st.rerun()
    except Exception as e:
        st.session_state.key_valid = False
        st.error(f"Key failed: {str(e)[:120]}")

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

# ────── PAGE SETUP ──────
st.set_page_config(page_title="Dojo", page_icon="🥋", layout="wide")
st.title(f"Dojo — {st.session_state.user_name}'s Nightly Ritual")

# First-time name
if st.session_state.user_name == "there":
    name = st.text_input("First, what should I call you?", placeholder="e.g., Abi")
    if st.button("Save Name") or name:
        st.session_state.user_name = name.strip() or "Warrior"
        st.rerun()

end_day_carry_over()

# ────── SIDEBAR — AI COACH ──────
with st.sidebar:
    st.header(f"Dojo Master for {st.session_state.user_name}")

    # OpenAI key input + test
    api_key = st.text_input("OpenAI API Key (for real AI coach)", type="password", key="openai_input")
    if api_key:
        st.session_state.openai_key = api_key
        if st.button("Test & Activate Key"):
            test_openai_key()

    # Status
    if st.session_state.key_valid:
        st.success("Real AI coach active!")
    elif st.session_state.openai_key:
        st.warning("Key pasted — hit Test & Activate")
    else:
        st.info("Paste OpenAI key → Test → Real coach unlocks")

    # Chat history
    for msg in st.session_state.ai_history[-10:]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    prompt = st.chat_input(f"Ask {st.session_state.user_name}'s coach anything…")
    if prompt:
        st.session_state.ai_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)

        task_summary = "\n".join(f"- {'Completed' if t.get('completed') else 'Open'} {t['text']}" for t in st.session_state.tasks)
        system_prompt = [
            {"role": "system", "content": f"You are Dojo Master — a wise, fun, slightly cheeky productivity coach for {st.session_state.user_name}. "
             f"Help with motivation, balance (especially fitness), and gentle nudges. Keep replies short, warm, and actionable. "
             f"Current streak: {st.session_state.streak} days | Points: {st.session_state.points}"},
            {"role": "user", "content": f"Tasks:\n{task_summary or 'None yet'}\n\nUser says: {prompt}"}
        ]
        reply = ai_chat(system_prompt)
        st.session_state.ai_history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"): st.write(reply)
        st.rerun()

    st.divider()
    st.metric("Total Points", st.session_state.points)
    st.metric("Streak", f"{st.session_state.streak} days")

# ────── MAIN TASK LIST ──────
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader(f"Tomorrow’s Dojo — {(datetime.now() + timedelta(days=1)).strftime('%b %d, %Y')}")

    with st.form("add_task", clear_on_submit=True):
        new = st.text_input("New task", placeholder="e.g., 30 min workout, Call mom")
        if st.form_submit_button("Add Task"):
            if new.strip():
                st.session_state.tasks.append({"text": new.strip(), "completed": False})
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

st.caption("Built with ❤️ by Grok & Abi — now powered by OpenAI GPT-4o-mini")
