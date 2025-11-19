import streamlit as st
from datetime import datetime, timedelta
import random
import os
import json  # For better error printing

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
GROK_API_KEY = st.secrets.get("GROK_API_KEY") if st.secrets else None
if not GROK_API_KEY:
    GROK_API_KEY = os.getenv("GROK_API_KEY")

# Sidebar key input (safe, no errors)
if "grok_key_set" not in st.session_state:
    st.session_state.grok_key_set = False

with st.sidebar:
    api_key = st.text_input("🔑 Grok API Key (paste here for smart AI)", type="password", key="api_key_input")
    if api_key and not st.session_state.grok_key_set:
        st.session_state.grok_key = api_key
        st.session_state.grok_key_set = True
        st.rerun()
    if st.session_state.get("grok_key"):
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
    
    try:
        import requests
        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "grok-4",  # Updated to current 2025 production model
                "messages": messages,
                "temperature": 0.8,
                "max_tokens": 150,
                "stream": False  # Explicit for stability
            },
            timeout=15
        )
        response.raise_for_status()  # Raise if 4xx/5xx error
        data = response.json()
        
        # Debug: Show full response if error (remove later if you want)
        if "error" in data:
            st.error(f"API Error: {json.dumps(data['error'], indent=2)}")
            return f"Hey {st.session_state.user_name}, API hiccup: {data['error'].get('message', 'Unknown')}. Mock mode on!"
        
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        st.error(f"Request failed: {str(e)}")
        return f"Hey {st.session_state.user_name}, network breather. (Details: {str(e)[:50]}...) Mock mode on!"
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        st.error(f"Parse error: {str(e)}. Raw response: {response.text[:200] if 'response' in locals() else 'No response'}")
        return f"Hey {st.session_state.user_name}, Grok's taking a quick breather. (Error: {str(e)[:50]}...) Mock mode on!"

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

# Ask name once (safe check)
if st.session_state.user_name == "there":
    name = st.text_input("First, what should I call you?", placeholder="Your name (e.g., Abi)")
    if st.button("Set Name") or name:
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

    prompt = st.chat_input(f"Ask {st.session_state.user_name}'s coach anything… (e.g., 'Suggest a fitness task')")
    if prompt:
        st.session_state.ai_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Build context for Grok
        task_summary = "\n".join(f"- {'✅' if t.get('completed') else '⭕'} {t['text']}" for t in st.session_state.tasks)
        system_prompt = [
            {"role": "system", "content": f"You are Dojo Master, a wise, fun, slightly cheeky AI coach for {st.session_state.user_name}. "
             f"Help with productivity, motivation, balance (especially fitness), and gentle nudges. Keep replies short (under 100 words), warm, and actionable. "
             f"Know their points: {st.session_state.points}, streak: {st.session_state.streak} days."},
            {"role": "user", "content": f"Current tasks:\n{task_summary or 'None yet'}\n\nUser says: {prompt}"}
        ]
        reply = grok_chat(system_prompt)
        st.session_state.ai_history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.write(reply)
        st.rerun()

    st.divider()
    st.metric("Total Points", st.session_state.points)
    st.metric("Streak", f"{st.session_state.streak} days 🔥")

# ────── MAIN TASKS ──────
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader(f"📋 Tomorrow’s Dojo — {(datetime.now() + timedelta(days=1)).strftime('%b %d, %Y')}")
    
    with st.form("add_task", clear_on_submit=True):
        new_task = st.text_input("New task", placeholder="e.g., 30 min workout, Call mom")
        if st.form_submit_button("Add Task"):
            if new_task.strip():
                st.session_state.tasks.append({"text": new_task.strip(), "completed": False})
                st.success(f"Added: {new_task.strip()}")
                st.rerun()

    # Score calc
    total_tasks = len(st.session_state.tasks)
    completed = sum(1 for t in st.session_state.tasks if t.get("completed", False))
    score = int((completed / total_tasks * 100) if total_tasks else 0)
    st.metric("Today's Score", f"{score}%")

    # Task list with fixed checkboxes
    for i, task in enumerate(st.session_state.tasks.copy()):
        cols = st.columns([4, 1, 1])
        with cols[0]:
            is_checked = st.checkbox(task["text"], value=task.get("completed", False), key=f"cb_{i}")
            if is_checked and not task.get("completed", False):
                task["completed"] = True
                st.session_state.points += 10
                st.balloons()
                st.rerun()
        with cols[1]:
            if st.button("✓", key=f"check_{i}", disabled=task.get("completed", False)):
                task["completed"] = True
                st.session_state.points += 
