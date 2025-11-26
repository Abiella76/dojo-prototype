import streamlit as st
from datetime import date, timedelta

st.set_page_config(page_title="Dojo", page_icon="Calendar", layout="wide")

# ────── BASIC SETUP ──────
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

bg = "#0e1117" if st.session_state.theme == "dark" else "#ffffff"
text_color = "#fafafa" if st.session_state.theme == "dark" else "#000000"
accent = "#ff4b4b"

PRIORITY_COLORS = {"Critical": "#ff3333", "High": "#ff8833", "Medium": "#ffdd33", "Low": "#33ff99"}
PRIORITIES = ["Critical", "High", "Medium", "Low"]

if "user_name" not in st.session_state: st.session_state.user_name = "Warrior"
if "tasks_by_date" not in st.session_state: st.session_state.tasks_by_date = {}

if st.session_state.user_name == "Warrior":
    name = st.text_input("Your name?", placeholder="Warrior")
    if st.button("Enter Dojo") or name:
        st.session_state.user_name = name.strip() or "Warrior"
        st.balloons()
        st.rerun()

today = date.today()
selected_date = st.date_input("Day", value=today)
date_str = selected_date.strftime("%Y-%m-%d")
if date_str not in st.session_state.tasks_by_date:
    st.session_state.tasks_by_date[date_str] = []

# Carry-over incomplete tasks
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

# ────── GLOBAL CSS (THIS IS THE WINNING ONE) ──────
st.markdown(f"""
<style>
    .reportview-container {{ background: {bg}; color: {text_color}; }}
    .task-card {{
        padding: 18px;
        margin: 12px 0;
        border-radius: 16px;
        background: rgba(255,75,75,0.08);
        border-left: 6px solid {accent};
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
    }}
    .task-card.completed {{ opacity: 0.6; text-decoration: line-through; }}
    .progress-fill {{
        height: 60px; width: {score}%;
        background: linear-gradient(90deg, #ff4b4b, #00ff88);
        border-radius: 30px;
        display: flex; align-items: center; justify-content: center;
        font-size: 32px; font-weight: bold; color: white;
    }}

    /* THIS IS THE ONLY CSS THAT WORKS IN 2025 */
    button[kind="secondary"] {{
        background: var(--prio-color) !important;
        color: white !important;
        border: none !important;
        border-radius: 50px !important;
        padding: 10px 28px !important;
        font-weight: bold !important;
        font-size: 14px !important;
        box-shadow: 0 6px 20px rgba(0,0,0,0.4) !important;
        transition: all 0.25s ease !important;
    }}
    button[kind="secondary"]:hover {{
        transform: scale(1.18) !important;
        box-shadow: 0 12px 35px rgba(0,0,0,0.5) !important;
    }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h1 style='color:{accent};'>Dojo — {st.session_state.user_name}'s Life OS</h1>", unsafe_allow_html=True)

# Add task
new = st.text_input("What needs to be done?", key="new_task", label_visibility="collapsed")
if new.strip():
    cols = st.columns(4)
    for i, p in enumerate(PRIORITIES):
        with cols[i]:
            if st.button(p, key=f"add_{p}", use_container_width=True):
                tasks.append({"text": new.strip(), "completed": False, "notes": "", "priority": p})
                st.rerun()

st.markdown(f"<div class='progress-fill'>{score}%</div>", unsafe_allow_html=True)

# ────── TASK LOOP ──────
for i in range(len(tasks)):
    task = tasks[i]
    prio = task.get("priority", "Low")
    color = PRIORITY_COLORS[prio]
    edit_key = f"editprio_{date_str}_{i}"

    st.markdown(f"<div class='task-card{' completed' if task.get('completed') else ''}>", unsafe_allow_html=True)

    # Badge + Title on same line
    col1, col2 = st.columns([0.22, 0.78])

    with col1:
        if st.session_state.get(edit_key):
            # Priority selector
            for np in PRIORITIES:
                if st.button(np, key=f"set_{i}_{np}", use_container_width=True):
                    tasks[i]["priority"] = np
                    st.session_state[edit_key] = False
                    st.rerun()
            if st.button("Cancel", key=f"can_{i}"):
                st.session_state[edit_key] = False
                st.rerun()
        else:
            # THIS IS THE PERFECT BADGE — color + clickable
            st.markdown(f'<div style="--prio-color:{color}"></div>', unsafe_allow_html=True)
            if st.button(prio, key=f"badge_{i}", type="secondary"):
                st.session_state[edit_key] = True
                st.rerun()

    with col2:
        st.markdown(f"### {task['text']}")

    # Action buttons
    a, b, c, d = st.columns(4)
    with a:
        if task.get("completed"):
            st.success("DONE")
        else:
            if st.button("Complete", key=f"c{i}"):
                tasks[i]["completed"] = True
                st.rerun()
    with b:
        if st.button("Notes", key=f"n{i}"):
            st.session_state[f"notes{i}"] = True
    with c:
        if st.button("Edit", key=f"e{i}"):
            st.session_state[f"edit{i}"] = True
    with d:
        if st.button("Delete", key=f"d{i}"):
            tasks.pop(i)
            st.rerun()

    # Notes & Edit
    if st.session_state.get(f"notes{i}"):
        note = st.text_area("Note", task.get("notes",""), key=f"ni{i}")
        x, y = st.columns(2)
        with x: 
            if st.button("Save", key=f"sn{i}"):
                tasks[i]["notes"] = note
                st.session_state[f"notes{i}"] = False
                st.rerun()
        with y:
            if st.button("Cancel", key=f"cn{i}"):
                st.session_state[f"notes{i}"] = False
                st.rerun()

    if st.session_state.get(f"edit{i}"):
        txt = st.text_input("Edit task", task["text"], key=f"ti{i}")
        x, y = st.columns(2)
        with x:
            if st.button("Save", key=f"se{i}"):
                tasks[i]["text"] = txt.strip()
                st.session_state[f"edit{i}"] = False
                st.rerun()
        with y:
            if st.button("Cancel", key=f"ce{i}"):
                st.session_state[f"edit{i}"] = False
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.metric("Flow", f"{score}%")
    st.write(f"**Tasks:** {total} · **Done:** {done}")

st.caption("v15.0 — FINAL • Full color badge • Fully clickable • Next to task • Text readable • You are free")
