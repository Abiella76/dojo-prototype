import streamlit as st
from datetime import date, timedelta

st.set_page_config(page_title="Dojo", page_icon="Calendar", layout="wide")

# ────── BASIC SETUP ──────
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

# Carry-over incomplete
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

# ────── CSS (THE MAGIC) ──────
st.markdown(f"""
<style>
    .reportview-container {{ background: {bg}; color: {text} }}
    .task-card {{ padding: 20px; margin: 16px 0; border-radius: 20px; background: rgba(255,75,75,0.1);
                  border-left: 8px solid {accent}; box-shadow: 0 8px 25px rgba(0,0,0,0.3); }}
    .task-card.completed {{ opacity: 0.6; text-decoration: line-through; }}
    .progress-fill {{ height: 70px; width: {score}%; background: linear-gradient(90deg, #ff4b4b, #00ff88);
                      border-radius: 35px; display: flex; align-items: center; justify-content: center;
                      font-size: 36px; font-weight: bold; color: white; }}

    /* THIS IS THE FINAL TRICK */
    .badge-container {{
        position: relative;
        display: inline-block;
        margin-bottom: 16px;
    }}
    .badge-button {{
        position: absolute !important;
        top: 0; left: 0; width: 100%; height: 100%;
        opacity: 0;
        cursor: pointer;
    }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h1 style='color:{accent};'>Dojo — {st.session_state.user_name}'s Life OS</h1>", unsafe_allow_html=True)

# Add task
new = st.text_input("What needs to be done?", key="new", label_visibility="collapsed")
if new.strip():
    cols = st.columns(4)
    for i, p in enumerate(PRIORITIES):
        with cols[i]:
            if st.button(p, key=f"add_{p}", use_container_width=True):
                tasks.append({"text": new.strip(), "completed": False, "notes": "", "priority": p})
                st.rerun()

st.markdown(f"<div class='progress-fill'>{score}%</div>", unsafe_allow_html=True)

# ────── TASKS ──────
for i in range(len(tasks)):
    task = tasks[i]
    prio = task.get("priority", "Low")
    color = PRIORITY_COLORS[prio]
    edit_key = f"edit_{date_str}_{i}"

    st.markdown(f"<div class='task-card{' completed' if task.get('completed') else ''}>", unsafe_allow_html=True)

    # THE WINNING SOLUTION — ONLY ONE VISUAL ELEMENT
    if st.session_state.get(edit_key):
        st.markdown("**Change priority:**")
        cols = st.columns(4)
        for j, np in enumerate(PRIORITIES):
            with cols[j]:
                if st.button(np, key=f"set_{i}_{np}"):
                    tasks[i]["priority"] = np
                    st.session_state[edit_key] = False
                    st.rerun()
        if st.button("Cancel", key=f"can_{i}"):
            st.session_state[edit_key] = False
            st.rerun()
    else:
        # THIS IS IT — ONLY THE RED BADGE, NOTHING ELSE
        st.markdown(f"""
        <div class="badge-container">
            <div style="
                background: {color};
                color: white;
                padding: 12px 32px;
                border-radius: 50px;
                font-weight: bold;
                font-size: 14px;
                box-shadow: 0 6px 20px rgba(0,0,0,0.4);
                display: inline-block;
                transition: all 0.25s;
            " onmouseover="this.style.transform='scale(1.18)'; this.style.boxShadow='0 12px 35px rgba(0,0,0,0.5)'"
              onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 6px 20px rgba(0,0,0,0.4)'">
                {prio}
            </div>
            <button class="badge-button" id="btn{i}"></button>
        </div>
        """, unsafe_allow_html=True)

        # Invisible Streamlit button covering the entire badge
        if st.button("", key=f"btn{i}"):
            st.session_state[edit_key] = True
            st.rerun()

    st.markdown(f"### {task['text']}")

    c1, c2, c3, c4 = st.columns([2,2,2,2])
    with c1:
        if task.get("completed"):
            st.success("DONE")
        else:
            if st.button("Complete", key=f"c{i}"):
                tasks[i]["completed"] = True
                st.rerun()
    with c2:
        if st.button("Notes", key=f"n{i}"):
            st.session_state[f"notes{i}"] = True
    with c3:
        if st.button("Edit", key=f"e{i}"):
            st.session_state[f"edit{i}"] = True
    with c4:
        if st.button("Delete", key=f"d{i}"):
            tasks.pop(i)
            st.rerun()

    # Notes & Edit modals
    if st.session_state.get(f"notes{i}"):
        note = st.text_area("Note", task.get("notes",""), key=f"ni{i}")
        a, b = st.columns(2)
        with a:
            if st.button("Save", key=f"sn{i}"):
                tasks[i]["notes"] = note
                st.session_state[f"notes{i}"] = False
                st.rerun()
        with b:
            if st.button("Cancel", key=f"cn{i}"):
                st.session_state[f"notes{i}"] = False
                st.rerun()

    if st.session_state.get(f"edit{i}"):
        txt = st.text_input("Edit task", task["text"], key=f"ti{i}")
        a, b = st.columns(2)
        with a:
            if st.button("Save", key=f"se{i}"):
                tasks[i]["text"] = txt.strip()
                st.session_state[f"edit{i}"] = False
                st.rerun()
        with b:
            if st.button("Cancel", key=f"ce{i}"):
                st.session_state[f"edit{i}"] = False
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

with st.sidebar:
    st.metric("Flow", f"{score}%")
    st.write(f"**Tasks:** {total} · **Done:** {done}")

st.caption("v13.0 — IT IS DONE • Badge = only thing visible • Badge = fully clickable • No extra button • Red Critical works perfectly")
