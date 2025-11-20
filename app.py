import streamlit as st
from datetime import datetime, timedelta
import random
import openai

# ────── SESSION STATE INIT ──────
defaults = {
    "tasks": [], "points": 0, "streak": 0,
    "last_date": datetime.now().date(),
    "ai_history": [], "user_name": "there",
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
        fallbacks = [
            f"Strong move, {st.session_state.user_name}!",
            f"Keep the streak alive, {st.session_state.user_name}",
            f"Quick nudge from your coach, {st.session_state.user_name}!",
            f"Tomorrow-you is proud, {st.session_state.user_name}!"
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
        st.error(f"OpenAI error: {str(e)[:100]}")
        return "Coach is taking a quick breather — mock mode on!"

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

# ────── VOICE INPUT ──────
voice_html = """
<script>
    const mic = document.createElement('button');
    mic.innerHTML = 'Voice input';
    mic.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;padding:16px 20px;border-radius:50%;background:#ff4b4b;color:white;border:none;box-shadow:0 4px 20px rgba(0,0,0,0.3);font-size:18px;cursor:pointer;';
    mic.onclick = () => {
        const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.start();
        mic.innerHTML = 'Listening…';
        recognition.onresult = (event) => {
            const text = event.results[0][0].transcript;
            const input = parent.document.querySelector('input[data-testid="stTextInput"]');
            if (input) input.value = text;
        };
        recognition.onerror = () => mic.innerHTML = 'Voice input';
        recognition.onend = () => mic.innerHTML = 'Voice input';
    };
    document.body.appendChild(mic);
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
            st.write(msg["content"])

    prompt = st.chat_input(f"Ask {st.session_state.user_name}'s coach…")
    if prompt:
        st.session_state.ai_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        task_summary = "\n".join(f"- {'Completed' if t.get('completed') else 'Open'} {t['text']}" for t in st.session_state.tasks)
        system = [
            {"role": "system", "content": f"Wise, fun, cheeky Dojo Master for {st.session_state.user_name}. Streak: {st.session_state.streak} | Points: {st.session_state.points}"},
            {"role": "user", "content": f"Tasks:\n{task_summary or 'None'}\n\n{prompt}"}
        ]
        reply = ai_chat(system)
        st.session_state.ai_history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"): st.write(reply)
        st.rerun()

    st.divider()
    st.metric("Total Points", st.session_state.points)
    st.metric("Streak", f"{st.session_state.streak} days")

# ────── MAIN TASKS ──────
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader(f"Tomorrow’s Dojo — {(datetime.now() + timedelta(days=1)).strftime('%b %d, %Y')}")

    voice_result = st.text_input("", key="voice_result", label_visibility="collapsed")

    with st.form("add_task", clear_on_submit=True):
        new_task = st.text_input("New task", placeholder="Type or tap red Voice input button → speak!", value=voice_result)
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

        # Editing mode
        if st.session_state.editing_task == i:
            edited_text = st.text_input("Edit task", value=task["text"], key=f"edit_input_{i}")
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.button("Save", key=f"save_{i}"):
                    st.session_state.tasks[i]["text"] = edited_text.strip()
                    st.session_state.editing_task = None
                    st.rerun()
            with col_cancel:
                if st.button("Cancel", key=f"cancel_{i}"):
                    st.session_state.editing_task = None
                    st.rerun()

        # Normal mode
        else:
            with cols[0]:
                # Fully dynamic checkbox: check AND uncheck update points + score
                was_completed = task.get("completed", False)
                checked = st.checkbox(task["text"], value=was_completed, key=f"cb_{i}")

                if checked != was_completed:
                    task["completed"] = checked
                    if checked:
                        st.session_state.points += 10
                        st.balloons()
                    else:
                        st.session_state.points = max(0, st.session_state.points - 10)  # prevent negative
                    st.rerun()

            with cols[1]:
                if st.button("Edit", key=f"edit_{i}"):
                    st.session_state.editing_task = i
                    st.rerun()

            with cols[2]:
                if st.button("Delete", key=f"del_{i}"):
                    st.session_state.tasks.pop(i)
                    st.rerun()

with c2:
    st.write(f"**Left:** {total - done}")
    if st.button("End Day & Carry Over", type="primary", use_container_width=True):
        end_day_carry_over()

st.caption("Built with love by Grok & Abi — now with fully dynamic check/uncheck!")
