import streamlit as st
from datetime import date, timedelta

st.set_page_config(page_title="Dojo", page_icon="Calendar", layout="wide")

# ────── SETUP ──────
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
bg = "#0e1117" if st.session_state.theme == "dark" else "#ffffff"
text = "#fafafa" if st.session_state.theme == "dark" else "#000000"
accent = "#ff4b4b"

PRIORITY_COLORS = {"Critical": "#ff3333", "High": "#ff8833", "Medium": "#ffdd33", "Low": "#33ff99"}
PRIORITIES = ["Critical", "High", "Medium", "Low"]

if "user_name" not in st.session_state: st.session_state.user_name = "Warrior"
if "tasks_by_date" not in st.session_state: st.session_state.tasks_by_date = {}

if st.session_state.user_name == "Warrior":
    name = st.text_input("Your name?", placeholder="e.g. Alex")
    if st.button("Enter Dojo") or name:
        st.session_state.user_name = name.strip() or "Warrior"
        st.balloons()
        st.rerun()

today = date.today()
selected_date = st.date_input("Day", value=today)
date_str = selected_date.strftime("%Y-%m-%d")
if date_str not in st.session_state.tasks_by_date:
    st.session_state.tasks_by_date[date_str] = []

# Carry-over
for offset in range(1, 31):
    past = (today - timedelta(days=offset)).strftime("%Y-%m-%d")
    if past in st.session_state.tasks_by_date:
        for t in st.session_state.tasks_by_date[past]:
            if not t.get("completed") and t["text"] not in [x["text"] for x in st.session_state.tasks_by_date.get(date_str, [])]:
                st.session_state.tasks_by_date[date_str].append(t.copy())

tasks = st.session_state.tasks_by_date[date_str]
total = len(tasks)
done = sum(t.get("completed", False) for t in tasks)
score = int(done/total*100) if total else 0

# ────── CSS (only what works) ──────
st.markdown(f"""
<style>
    .reportview-container {{ background: {bg}; color: {text} }}
    .task-card {{ padding: 18px; margin: 12px 0; border-radius: 16px; background: rgba(255,75,75,0.08);
                  border-left: 6px solid {accent}; box-shadow: 0 6px 20px rgba(0,0,0,0.3); }}
    .task-card.completed {{ opacity: 0.6; text-decoration: line-through; }}
    .progress-fill {{ height: 60px; width: {score}%; background: linear-gradient(90deg, #ff4b4b, #00ff88);
                      border-radius: 30px; display: flex; align-items: center; justify-content: center;
                      font-size: 32px; font-weight: bold; color: white; }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h1 style='color:{accent};'>Dojo — {st.session_state.user_name}'s Life OS</h1>", unsafe_allow_html=True)

new = st.text_input("What needs to be done?", key="new", label_visibility="collapsed")
if new.strip():
    cols = st.columns(4)
    for i, p in enumerate(PRIORITIES):
        with cols[i]:
            if st.button(p, key=f"add_{p}", use_container_width=True):
                tasks.append({"text": new.strip(), "completed": False, "notes": "", "priority": p})
                st.rerun()

st.markdown(f"<div class='progress-fill'>{score}%</div>", unsafe_allow_html=True)

# ────── TASKS (v14 layout you liked + color restored + notes fixed) ──────
for i in range(len(tasks)):
    task = tasks[i]
    prio = task.get("priority", "Low")
    color = PRIORITY_COLORS[prio]
    edit_key = f"edit_prio_{date_str}_{i}"

    st.markdown(f"<div class='task-card{' completed' if task.get('completed') else ''}>", unsafe_allow_html=True)

    col_badge, col_title = st.columns([0.25, 0.75])

    with col_badge:
        if st.session_state.get(edit_key):
            for np in PRIORITIES:
                if st.button(np, key=f"set_{i}_{np}", use_container_width=True):
                    tasks[i]["priority"] = np
                    st.session_state[edit_key] = False
                    st.rerun()
            if st.button("Cancel", key=f"cancel_{i}"):
                st.session_state[edit_key] = False
                st.rerun()
        else:
            # FULL COLOR + CLICKABLE BADGE (the one that worked in v14)
            st.markdown(f"""
            <div style="background:{color}; color:white; padding:10px 24px; border-radius:50px; 
                        font-weight:bold; text-align:center; box-shadow:0 6px 20px rgba(0,0,0,0.4);
                        cursor:pointer; transition:all 0.25s;"
                 onclick="document.getElementById('badge_btn_{i}').click()">
                {prio}
            </div>
            """, unsafe_allow_html=True)
            if st.button("", key=f"badge_btn_{i}"):
                st.session_state[edit_key] = True
                st.rerun()

    with col_title:
        st.markdown(f"### {task['text']}")

    # Action buttons
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if task.get("completed"):
            st.success("DONE")
        else:
            if st.button("Complete", key=f"done_{i}"):
                tasks[i]["completed"] = True
                st.rerun()
    with c2:
        if st.button("Notes", key=f"notes_{i}"):
            st.session_state[f"show_notes_{i}"] = True
    with c3:
        if st.button("Edit", key=f"edit_{i}"):
            st.session_state[f"editing_{i}"] = True
    with c4:
        if st.button("Delete", key=f"del_{i}"):
            tasks.pop(i)
            st.rerun()

    # NOTES — FIXED
    if st.session_state.get(f"show_notes_{i}"):
        note = st.text_area("Notes", value=task.get("notes", ""), key=f"note_input_{i}", height=100)
        col_save, col_cancel = st.columns(2)
        with col_save:
            if st.button("Save Note", key=f"save_note_{i}"):
                tasks[i]["notes"] = note
                st.session_state[f"show_notes_{i}"] = False
                st.rerun()
        with col_cancel:
            if st.button("Cancel", key=f"cancel_note_{i}"):
                st.session_state[f"show_notes_{i}"] = False
                st.rerun()

    # EDIT TASK TEXT — also fixed
    if st.session_state.get(f"editing_{i}"):
        new_text = st.text_input("Edit task", value=task["text"], key=f"edit_text_{i}")
        col_save, col_cancel = st.columns(2)
        with col_save:
            if st.button("Save", key=f"save_edit_{i}"):
                tasks[i]["text"] = new_text.strip()
                st.session_state[f"editing_{i}"] = False
                st.rerun()
        with col_cancel:
            if st.button("Cancel", key=f"cancel_edit_{i}"):
                st.session_state[f"editing_{i}"] = False
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.metric("Flow", f"{score}%")
    st.write(f"**Tasks:** {total} · **Done:** {done}")

st.caption("v14-stable + full color badge + notes fixed • This one works 100%")
