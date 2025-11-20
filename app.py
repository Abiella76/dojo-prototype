import streamlit as st
from datetime import date, timedelta
import random
import openai

# ────── SESSION STATE INIT ──────
defaults = {
    "tasks_by_date": {},      # {"2025-11-20": [{"text": "...", "completed": False}, ...]}
    "points": 0,
    "streak_dates": set(),
    "user_name": "there",
    "openai_key": "",
    "key_valid": False,
    "editing_task": None,
    "ai_history": []
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ────── OPENAI CHAT ──────
def ai_chat(messages):
    key = st.session_state.get("openai_key", "")
    if not key or not st.session_state.get("key_valid", False):
        fallbacks = [
            f"Nice one, {st.session_state.user_name}!",
            f"Keep the streak alive, {st.session_state.user_name}!",
            f"Tomorrow-you is proud, {st.session_state.user_name}!"
        ]
        return random.choice(fallbacks)
    try:
        client = openai.OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.8,
            max_tokens=150
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return "Coach warming up — mock mode!"

def test_openai_key():
    key = st.session_state.get("openai_key", "")
    if not key:
        st.error("Paste a key first!")
        return
    try:
        client = openai.OpenAI(api_key=key)
        client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":"ok"}], max_tokens=5)
        st.session_state.key_valid = True
        st.success("Real AI coach active!")
        st.rerun()
    except Exception as e:
        st.session_state.key_valid = False
        st.error(f"Key failed: {str(e)[:120]}")

# ────── VOICE INPUT (mobile) ──────
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

# ────── PAGE SETUP ──────
st.set_page_config(page_title="Dojo Calendar", page_icon="Calendar", layout="wide")
st.title(f"Dojo Calendar — {st.session_state.user_name}'s Life OS")

# Name entry (fixed indentation)
if st.session_state.user_name == "there":
    name = st.text_input("First, what should I call you?", placeholder="e.g., Abi")
    if st.button("Save Name") or name:
        st.session_state.user_name = name.strip() or "Warrior"
        st.rerun()

# ────── CALENDAR & DATE SELECTION ──────
today = date.today()
selected_date = st.date_input("Pick a date", value=today)
date_str = selected_date.strftime("%Y-%m-%d")

if date_str not in st.session_state.tasks_by_date:
    st.session_state.tasks_by_date[date_str] = []

tasks = st.session_state.tasks_by_date[date_str]
total = len(tasks)
done = sum(1 for t in tasks if t.get("completed"))
score = int(done/total*100) if total else 0

# Streak: any completed task on a day counts
if any(t.get("completed") for t in tasks):
    st.session_state.streak_dates.add(date_str)

streak = 0
check_date = today
while check_date.strftime("%Y-%m-%d") in st.session_state.streak_dates:
    streak += 1
    check_date -= timedelta(days=1)

# ────── SIDEBAR COACH ──────
with st.sidebar:
    st.header("Dojo Master")
    api_key = st.text_input("OpenAI API Key", type="password", key="openai_input")
    if api_key:
        st.session_state.openai_key = api_key
        if st.button("Test & Activate Key"):
            test_openai_key()

    st.write("Real AI active!" if st.session_state.key_valid else "Paste key → Test")

    for msg in st.session_state.ai_history[-10:]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    prompt = st.chat_input(f"Ask coach about {selected_date.strftime('%b %d')}…")
    if prompt:
        task_summary = "\n".join(f"- {'Completed' if t.get('completed') else 'Open'} {t['text']}" for t in tasks)
        system = [
            {"role": "system", "content": f"Dojo Master for {st.session_state.user_name}. Planning {selected_date.strftime('%A, %b %d')}. Streak: {streak} days."},
            {"role": "user", "content": f"Tasks:\n{task_summary or 'None'}\n\n{prompt}"}
        ]
        reply = ai_chat(system)
        st.session_state.ai_history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.write(reply)

    st.divider()
    st.metric("Current Streak", f"{streak} days")
    st.metric(f"{selected_date.strftime('%b %d')} Score", f"{score}%")

# ────── MAIN TASKS FOR SELECTED DATE ──────
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader(f"{selected_date.strftime('%A, %B %d, %Y')}")

    voice_result = st.text_input("", key="voice_result", label_visibility="collapsed")

    with st.form("add_task", clear_on_submit=True):
        new_task = st.text_input("New task", placeholder="Type or speak → Add", value=voice_result)
        if st.form_submit_button("Add Task") and new_task.strip():
            tasks.append({"text": new_task.strip(), "completed": False})
            st.rerun()

    for i, task in enumerate(tasks.copy()):
        cols = st.columns([4, 1, 1])

        # Editing mode
        if st.session_state.editing_task == f"{date_str}_{i}":
            edited = st.text_input("Edit task", value=task["text"], key=f"edit_{date_str}_{i}")
            cs, cc = st.columns(2)
            with cs:
                if st.button("Save", key=f"save_{date_str}_{i}"):
                    tasks[i]["text"] = edited.strip()
                    st.session_state.editing_task = None
                    st.rerun()
            with cc:
                if st.button("Cancel", key=f"cancel_{date_str}_{i}"):
                    st.session_state.editing_task = None
                    st.rerun()
        # Normal mode
        else:
            with cols[0]:
                was = task.get("completed", False)
                checked = st.checkbox(task["text"], value=was, key=f"cb_{date_str}_{i}")
                if checked != was:
                    task["completed"] = checked
                    st.rerun()

            with cols[1]:
                if st.button("Edit", key=f"edit_{date_str}_{i}"):
                    st.session_state.editing_task = f"{date_str}_{i}"
                    st.rerun()
            with cols[2]:
                if st.button("Delete", key=f"del_{date_str}_{i}"):
                    tasks.pop(i)
                    st.rerun()

with c2:
    st.write(f"**Tasks left:** {total - done}")
    if st.button("Clear completed tasks", type="secondary"):
        st.session_state.tasks_by_date[date_str] = [t for t in tasks if not t.get("completed")]
        st.rerun()

st.caption("Built with love by Grok & Abi — Full AI Calendar v5.0")
