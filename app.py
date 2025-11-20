import streamlit as st
from datetime import date, timedelta
import random
import openai

# ────── FORCE DARK/LIGHT THEME FIRST ──────
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

theme = st.session_state.theme
bg = "#0e1117" if theme == "dark" else "#fafafa"
text = "#fafafa" if theme == "dark" else "#0e1117"
accent = "#ff4b4b"

# ────── PAGE CONFIG & CSS ──────
st.set_page_config(page_title="Dojo Calendar", page_icon="Calendar", layout="wide")

st.markdown(f"""
<style>
    .reportview-container {{ background: {bg}; color: {text} }}
    .sidebar .sidebar-content {{ background: {bg} }}
    .stButton>button {{ background: {accent}; color: white; border-radius: 12px; border: none; }}
    .task-card {{ padding: 14px; margin: 10px 0; border-radius: 16px; background: rgba(255,75,75,0.1); border-left: 5px solid {accent}; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }}
    .completed {{ text-decoration: line-through; opacity: 0.6; }}
    .big-score {{ font-size: 64px; font-weight: bold; text-align: center; color: {accent}; margin: 20px 0; }}
</style>
""", unsafe_allow_html=True)

# ────── HEADER WITH THEME TOGGLE (NOW SAFE) ──────
col1, col2 = st.columns([10,1])
with col1:
    st.markdown(f"<h1 style='color:{accent}; margin:0;'>Dojo Calendar — {st.session_state.get('user_name','Warrior')}'s Life OS</h1>", unsafe_allow_html=True)
with col2:
    if st.button("Moon" if theme == "dark" else "Sun", key="theme_toggle"):
        toggle_theme()
        st.rerun()

# ────── REST OF SESSION STATE ──────
defaults = {
    "tasks_by_date": {}, "streak_dates": set(), "user_name": "there",
    "openai_key": "", "key_valid": False, "editing_task": None, "ai_history": []
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Name entry
if st.session_state.user_name == "there":
    name = st.text_input("What should I call you, warrior?", placeholder="e.g., Abi")
    if st.button("Enter the Dojo") or name:
        st.session_state.user_name = name.strip() or "Warrior"
        st.balloons()
        st.rerun()

# ────── CALENDAR ──────
today = date.today()
selected_date = st.date_input("Choose your day", value=today, key="date_picker")
date_str = selected_date.strftime("%Y-%m-%d")

if date_str not in st.session_state.tasks_by_date:
    st.session_state.tasks_by_date[date_str] = []

tasks = st.session_state.tasks_by_date[date_str]
total = len(tasks)
done = sum(1 for t in tasks if t.get("completed"))
score = int(done/total*100) if total else 0

# Streak
if any(t.get("completed") for t in tasks):
    st.session_state.streak_dates.add(date_str)

streak = 0
check = today
while check.strftime("%Y-%m-%d") in st.session_state.streak_dates:
    streak += 1
    check -= timedelta(days=1)

# ────── SIDEBAR COACH ──────
with st.sidebar:
    st.markdown("### Dojo Master")
    api_key = st.text_input("OpenAI Key", type="password")
    if api_key and api_key != st.session_state.openai_key:
        st.session_state.openai_key = api_key
        if st.button("Activate Real AI"):
            try:
                openai.OpenAI(api_key=api_key).chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":"hi"}], max_tokens=5)
                st.session_state.key_valid = True
                st.success("AI Master Awakened")
                st.rerun()
            except:
                st.error("Bad key")

    status = "Real AI active!" if st.session_state.key_valid else "Mock mode"
    st.write(status)

    for msg in st.session_state.ai_history[-8:]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input(f"Ask about {selected_date.strftime('%b %d')}…"):
        task_summary = "\n".join(f"- {'Completed' if t.get('completed') else 'Open'} {t['text']}" for t in tasks)
        messages = [
            {"role": "system", "content": f"Wise, fun Dojo Master for {st.session_state.user_name}. Planning {selected_date.strftime('%A, %b %d')}. Streak: {streak} days."},
            {"role": "user", "content": f"Tasks:\n{task_summary or 'None'}\n\n{prompt}"}
        ]
        reply = "Crushing it!"  # fallback
        if st.session_state.key_valid:
            try:
                resp = openai.OpenAI(api_key=st.session_state.openai_key).chat.completions.create(model="gpt-4o-mini", messages=messages, temperature=0.8, max_tokens=150)
                reply = resp.choices[0].message.content.strip()
            except:
                reply = "AI took a quick nap"
        else:
            reply = random.choice(["You're on fire!", "Keep stacking wins!", "Streak growing!"])

        st.session_state.ai_history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)

    st.divider()
    st.markdown(f"### Streak: {streak} days")
    st.metric("Flow Score", f"{score}%")

# ────── MAIN AREA ──────
c1, c2 = st.columns([2,1])

with c1:
    st.markdown(f"### {selected_date.strftime('%A, %B %d, %Y')}")
    st.markdown(f"<div class='big-score'>{score}%</div>", unsafe_allow_html=True)

    voice = st.text_input("", key="voice_result", label_visibility="collapsed")
    with st.form("add", clear_on_submit=True):
        new = st.text_input("Add task", placeholder="Speak or type → Add", value=voice)
        if st.form_submit_button("Add") and new.strip():
            tasks.append({"text": new.strip(), "completed": False})
            st.rerun()

    for i, task in enumerate(tasks.copy()):
        completed = task.get("completed", False)
        with st.container():
            st.markdown(f"<div class='task-card{' completed' if completed else ''}>", unsafe_allow_html=True)
            cols = st.columns([5,1,1])

            if st.session_state.editing_task == f"{date_str}_{i}":
                edited = st.text_input("Edit", value=task["text"], key=f"e_{date_str}_{i}")
                sa, ca = st.columns(2)
                with sa:
                    if st.button("Save", key=f"s_{date_str}_{i}"):
                        tasks[i]["text"] = edited.strip()
                        st.session_state.editing_task = None
                        st.rerun()
                with ca:
                    if st.button("Cancel", key=f"c_{date_str}_{i}"):
                        st.session_state.editing_task = None
                        st.rerun()
            else:
                with cols[0]:
                    was = task.get("completed", False)
                    checked = st.checkbox(task["text"], value=was, key=f"cb_{date_str}_{i}", label_visibility="collapsed")
                    if checked != was:
                        task["completed"] = checked
                        if checked and score == 100:
                            st.confetti()
                        elif checked:
                            st.balloons()
                        st.rerun()
                with cols[1]:
                    if st.button("Edit", key=f"edit_{date_str}_{i}"):
                        st.session_state.editing_task = f"{date_str}_{i}"
                        st.rerun()
                with cols[2]:
                    if st.button("Delete", key=f"del_{date_str}_{i}"):
                        tasks.pop(i)
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.write(f"**Left:** {total - done}")
    if st.button("Clear completed"):
        st.session_state.tasks_by_date[date_str] = [t for t in tasks if not t.get("completed")]
        st.rerun()

st.caption("Built with love by Grok & you — Gorgeous v6.0")
