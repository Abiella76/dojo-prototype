import streamlit as st
from datetime import datetime, date, timedelta
import random
import openai

# ────── SESSION STATE INIT ──────
defaults = {
    "tasks_by_date": {},   # {"2025-11-20": [{"text": "...", "completed": False}, ...], ...}
    "points": 0,
    "streak_dates": set(),
    "user_name": "there",
    "openai_key": "", "key_valid": False,
    "editing_task": None
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ────── OPENAI CHAT ──────
def ai_chat(messages):
    key = st.session_state.get("openai_key", "")
    if not key or not st.session_state.get("key_valid", False):
        fallbacks = [f"Nice one, {st.session_state.user_name}!", f"Keep building, {st.session_state.user_name}!"]
        return random.choice(fallbacks)
    try:
        client = openai.OpenAI(api_key=key)
        response = client.chat.completions.create(model="gpt-4o-mini", messages=messages, temperature=0.8, max_tokens=150)
        return response.choices[0].message.content.strip()
    except Exception as e:
        return "Coach is warming up — mock mode!"

def test_openai_key():
    key = st.session_state.get("openai_key", "")
    if not key:
        st.error("Paste a key first!")
        return
    try:
        client = openai.OpenAI(api_key=key)
        client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": "ok"}], max_tokens=5)
        st.session_state.key_valid = True
        st.success("Real AI coach active!")
        st.rerun()
    except Exception as e:
        st.session_state.key_valid = False
        st.error(f"Key failed: {str(e)[:120]}")

# ────── VOICE INPUT ──────
voice_html = """
<script>
    const mic = document.createElement('button');
    mic.innerHTML = 'Voice input';
    mic.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;padding:16px 20px;border-radius:50%;background:#ff4b4b;color:white;border:none;box-shadow:0 4px 20px rgba(0,0,0,0.3);font-size:18px;cursor:pointer;';
    mic.onclick = () => {
        const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.lang = 'en-US';
        recognition.start();
        mic.innerHTML = 'Listening…';
        recognition.onresult = (e) => {
            const text = e.results[0][0].transcript;
            const input = parent.document.querySelector('input[data-testid="stTextInput"]');
            if (input) input.value = text;
        };
        recognition.onend = () => mic.innerHTML = 'Voice input';
    };
    document.body.appendChild(mic);
</script>
"""
st.components.v1.html(voice_html, height=0, width=0)

# ────── PAGE ──────
st.set_page_config(page_title="Dojo Calendar", page_icon="Dojo", layout="wide")
st.title(f"Dojo Calendar — {st.session_state.user_name}'s Life OS")

if st.session_state.user_name == "there":
    name = st.text_input("First, what should I call you?", placeholder="e.g., Abi")
    if st.button("Save Name") or name:
        st.session_state.user_name = name.strip() or "Warrior"
        st.rerun()

# ────── CALENDAR & DATE SELECTION ──────
today = date.today()
selected_date = st.date_input("Select date", value=today, min_value=today - timedelta(days=365), max_value=today + timedelta(days=365))
date_str = selected_date.strftime("%Y-%m-%d")

# Initialize tasks for this date if missing
if date_str not in st.session_state.tasks_by_date:
    st.session_state.tasks_by_date[date_str] = []

tasks = st.session_state.tasks_by_date[date_str]
total = len(tasks)
done = sum(1 for t in tasks if t.get("completed"))
score = int(done/total*100) if total else 0

# Update streak (any completed task on a day = streak credit)
if any(t.get("completed") for t in tasks):
    st.session_state.streak_dates.add(date_str)

streak = 0
current = today
while current.strftime("%Y-%m-%d") in st.session_state.streak_dates:
    streak += 1
    current -= timedelta(days=1)

# ────── SIDEBAR COACH ──────
with st.sidebar:
    st.header(f"Dojo Master for {st.session_state.user_name}")
    api_key = st.text_input("OpenAI API Key", type="password", key="openai_input")
    if api_key:
        st.session_state.openai_key = api_key
        if st.button("Test & Activate Key"):
            test_openai_key()

    if st.session_state.key_valid:
        st.success("Real AI active!")

    for msg in st.session_state.get("ai_history", [])[-10:]:
        with st.chat_message(msg["role"]):
            st.write(msg["content
