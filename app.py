import streamlit as st
from datetime import date, timedelta
import random
import openai

# ────── DARK MODE + SESSION STATE ──────
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

theme = st.session_state.theme
bg = "#0e1117" if theme == "dark" else "#fafafa"
text = "#fafafa" if theme == "dark" else "#0e1117"
accent = "#ff4b4b"

st.set_page_config(page_title="Dojo Calendar", page_icon="Calendar", layout="wide")

# Custom CSS — this is where the magic happens
st.markdown(f"""
<style>
    .reportview-container {{ background: {bg}; color: {text} }}
    .sidebar .sidebar-content {{ background: {bg} }}
    .stButton>button {{ background: {accent}; color: white; border-radius: 12px; }}
    .task-card {{ padding: 12px; margin: 8px 0; border-radius: 12px; background: rgba(255,75,75,0.1); border-left: 4px solid {accent}; }}
    .completed {{ text-decoration: line-through; opacity: 0.6; }}
    .stProgress .st-bo {{ background: {accent} !important; }}
    .circle {{ font-size: 48px; }}
</style>
""", unsafe_allow_html=True)

# Header with theme toggle
col1, col2 = st.columns([6,1])
with col1:
    st.markdown(f"<h1 style='color:{accent};'>Dojo Calendar — {st.session_state.get('user_name','Warrior')}'s Life OS</h1>", unsafe_allow_html=True)
with col2:
    st.button("Moon" if theme == "dark" else "Sun", on_click=toggle_theme, key="theme")

# ────── SESSION STATE INIT ──────
defaults = {
    "tasks_by_date": {}, "streak_dates": set(), "user_name": "there",
    "openai_key": "", "key_valid": False, "editing_task": None, "ai_history": []
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Name entry
if st.session_state.user_name == "there":
    name = st.text_input("Warrior name?", placeholder="e.g., Abi")
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
streak = sum(1 for i in range(30) if (today - timedelta(days=i)).strftime("%Y-%m-%d") in st.session_state.streak_dates)

# ────── SIDEBAR COACH ──────
with st.sidebar:
    st.markdown(f"### Dojo Master")
    api_key = st.text_input("OpenAI Key", type="password", key="openai_input")
    if api_key:
        st.session_state.openai_key = api_key
        if st.button("Activate Real AI"):
            try:
                openai.OpenAI(api_key=api_key).chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":"ok"}], max_tokens=5)
                st.session_state.key_valid = True
                st.success("AI Master Awakened")
            except:
                st.error("Invalid key")

    # Chat
    for msg in st.session_state.ai_history[-8:]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input(f"Ask about {selected_date.strftime('%b %d')}…"):
        task_summary = "\n".join(f"- {'Completed' if t.get('completed') else 'Open'} {t['text']}" for t in tasks)
        system = [
            {"role": "system", "content": f"Wise, fun Dojo Master for {st.session_state.user_name}. Planning {selected_date.strftime('%A, %b %d')}. Streak: {streak} days."},
            {"role": "user", "content": f"Tasks:\n{task_summary or 'None'}\n\n{prompt}"}
        ]
        with st.chat_message("assistant"):
            reply = ai_chat(system) if st.session_state.key_valid else random.choice(["Crush it!", "You're unstoppable!", "Streak on fire!"])
            st.write(reply)
        st.session_state.ai_history.append({"role": "assistant", "content": reply})

    st.divider()
    st.markdown(f"### Streak: {streak} days")
    st.metric("Today's Flow", f"{score}%", delta=f"{done}/{total}")

# ────── MAIN AREA ──────
c1, c2 = st.columns([2,1])

with c1:
    st.markdown(f"### {selected_date.strftime('%A, %B %d, %Y')}")

    # Progress circle
    st.markdown(f"<div class='circle' style='color:{accent}; text-align:center;'>{score}%</div>", unsafe_allow_html=True)

    # Add task
    with st.form("add", clear_on_submit=True):
        voice = st.text_input("", key="voice_result", label_visibility="collapsed")
        new = st.text_input("New task", placeholder="Speak or type → Add", value=voice)
        if st.form_submit_button("Add Task") and new.strip():
            tasks.append({"text": new.strip(), "completed": False})
            st.rerun()

    # Tasks
    for i, task in enumerate(tasks.copy()):
        completed = task.get("completed", False)
        card_class = "task-card" + (" completed" if completed else "")
        
        with st.container():
            st.markdown(f"<div class='{card_class}'>", unsafe_allow_html=True)
            cols = st.columns([4,1,1])
            
            if st.session_state.editing_task == f"{date_str}_{i}":
                edited = st.text_input("Edit", value=task["text"], key=f"e_{date_str}_{i}")
                ca, cb = st.columns(2)
                with ca:
                    if st.button("Save", key=f"s_{date_str}_{i}"):
                        tasks[i]["text"] = edited.strip()
                        st.session_state.editing_task = None
                        st.rerun()
                with cb:
                    if st.button("Cancel", key=f"c_{date_str}_{i}"):
                        st.session_state.editing_task = None
                        st.rerun()
            else:
                with cols[0]:
                    was = task.get("completed", False)
                    checked = st.checkbox(task["text"], value=was, key=f"cb_{date_str}_{i}", label_visibility="collapsed")
                    if checked != was:
                        task["completed"] = checked
                        if checked and score == 100 and total > 0:
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
    if st.button("Clear completed", type="secondary"):
        st.session_state.tasks_by_date[date_str] = [t for t in tasks if not t.get("completed")]
        st.rerun()

st.caption("Built with love by Grok & you — now gorgeous v6.0")
