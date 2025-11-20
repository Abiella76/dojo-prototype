import streamlit as st
from datetime import datetime, timedelta
import random
import json
import openai

# ────── SESSION STATE INIT ──────
defaults = {
    "tasks": [], "points": 0, "streak": 0,
    "last_date": datetime.now().date(),
    "ai_history": [], "user_name": "there",
    "openai_key": "", "key_valid": False
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ────── OPENAI CHAT ──────
def ai_chat(messages):
    key = st.session_state.get("openai_key", "")
    if not key or not st.session_state.get("key_valid", False):
        fallbacks = [
            f"Strong move, {st.session_state.user_name}! That one’s going to feel amazing checked off.",
            f"You’re stacking wins like a pro, {st.session_state.user_name}. Keep the streak alive",
            f"Quick nudge: any movement on the list today, {st.session_state.user_name}?",
            f"Tomorrow-you is already thanking you, {st.session_state.user_name}!"
        ]
        return random.choice(fallbacks)

    try:
        client = openai.OpenAI(api_key=key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.8,
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"OpenAI hiccup: {str(e)[:100]}…")
        return f"Hey {st.session_state.user_name}, coach is warming up. Mock mode on!"

# ────── TEST KEY ──────
def test_openai_key():
    key = st.session_state.get("openai_key", "")
    if not key:
        st.error("Paste a key first!")
        return
    try:
        client = openai.OpenAI(api_key=key)
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'ok'"}],
            max_tokens=5
        )
        st.session_state.key_valid = True
        st.success("OpenAI key accepted! Real AI coach active")
        st.rerun()
    except Exception as e:
        st.session_state.key_valid = False
        st.error(f"Key failed: {str(e)[:120]}")

# ────── CARRY-OVER ──────
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

# ────── VOICE INPUT COMPONENT ──────
voice_html = """
<script>
const startBtn = window.parent.document.querySelector('button[kind="secondary"]');
if (startBtn && !startBtn.dataset.voice) {
    startBtn.dataset.voice = true;
    const mic = document.createElement('button');
    mic.innerHTML = 'Voice input';
    mic.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;padding:15px 20px;border-radius:50%;background:#ff4b4b;color:white;border:none;box-shadow:0 4px 15px rgba(0,0,0,0.3);font-size:18px;';
    mic.onclick = () => {
        const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.lang = 'en-US';
        recognition.start();
        mic.innerHTML = 'Listening…';
        recognition.onresult = (e) => {
            const text = e.results[0][0].transcript;
            window.parent.document.querySelector('input[aria-label="Voice result"]').value = text;
            mic.innerHTML = 'Voice input';
        };
        recognition.onerror = () => mic.innerHTML = 'Voice input';
        recognition.onend = () => mic.innerHTML = 'Voice input';
    };
    document.body.appendChild(mic);
}
</script>
"""
st.components.v1.html(voice_html, height=0, width=0)

# ────── PAGE ──────
st.set_page_config(page_title="Dojo", page_icon="Dojo", layout="wide")
st.title(f"Dojo — {st.session_state.user_name}'s Nightly Ritual")

if st.session_state.user_name == "there":
    name = st.text_input("First, what should I call you?", placeholder="e.g., Abi")
    if st.button("Save Name") or name:
        st.session_state.user_name = name.strip() or "Warrior"
        st.rerun()

end_day_carry_over()

# ────── SIDEBAR COACH ──────
with st.sidebar:
    st.header(f"Dojo Master for {st.session_state.user_name}")

    api_key = st.text_input("OpenAI API Key", type="password", key="openai_input")
    if api_key:
        st.session_state.openai_key = api_key
        if st.button("Test & Activate Key"):
            test_openai_key()

    if st.session_state.key_valid:
        st.success("Real AI coach active!")
    elif st.session_state.openai_key:
        st.warning("Key pasted — hit Test & Activate")

    for msg in st.session_state.ai_history[-10:]:
        with st.chat_message(msg["role"]):
            st.write(msg["content])

    prompt = st.chat_input(f"Ask {st.session_state.user_name}'s coach…")
    if prompt:
        st.session_state.ai_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)

        task_summary = "\n".join(f"- {'Completed' if t.get('completed') else 'Open'} {t['text']}" for t in st.session_state.tasks)
        system = [
            {"role": "system", "content": f"You are Dojo Master — wise, fun, cheeky coach for {st.session_state.user_name}. "
             f"Current streak: {st.session_state.streak} days | Points: {st.session_state.points}"},
            {"role": "user", "content": f"Tasks:\n{task_summary or 'None'}\n\n{prompt}"}
        ]
        reply = ai_chat(system)
        st.session_state.ai_history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"): st.write(reply)
        st.rerun()

    st.divider()
    st.metric("Total Points", st.session_state.points)
    st.metric("Streak", f"{st.session_state.streak} days")

# ────── MAIN TASKS + VOICE ──────
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader(f"Tomorrow’s Dojo — {(datetime.now() + timedelta(days=1)).strftime('%b %d, %Y')}")

    # Voice result hidden input
    voice_text = st.text_input("Voice result", key="voice_result", label_visibility="collapsed")

    with st.form("add_task", clear_on_submit=True):
        new = st.text_input(
            "New task",
            placeholder="Type or tap Voice input on mobile → speak!",
            value=voice_text
        )
        col_btn, col_voice = st.columns([1, 4])
        with col_btn:
            submitted = st.form_submit_button("Add Task")
        if submitted and new.strip():
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

st.caption("Built with ❤️ by Grok & Abi — now with voice input on mobile!")
