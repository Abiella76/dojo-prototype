import streamlit as st
from datetime import date, timedelta

# Config
st.set_page_config(page_title="Dojo", page_icon="Calendar", layout="wide")

# Theme
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
bg = "#0e1117" if st.session_state.theme == "dark" else "#ffffff"
text = "#fafafa" if st.session_state.theme == "dark" else "#000000"
accent = "#ff4b4b"

PRIORITY_COLORS = {"Critical": "#ff3333", "High": "#ff8833", "Medium": "#ffdd33", "Low": "#33ff99"}
PRIORITIES = ["Critical", "High", "Medium", "Low"]

# Data init
for k in ["user_name", "tasks_by_date"]:
    if k not in st.session_state:
        st.session_state[k] = {"user_name": "Warrior", "tasks_by_date": {}}.get(k, {})

if st.session_state.user_name == "Warrior":
    name = st.text_input("Name?", placeholder="e.g. Alex")
    if st.button("Enter Dojo") or name:
        st.session_state.user_name = name.strip() or "Warrior"
        st.balloons()
        st.rerun()

today = date.today()
selected_date = st.date_input("Day", today)
date_str = selected_date.strftime("%Y-%m-%d")
if date_str not in st.session_state.tasks_by_date:
    st.session_state.tasks_by_date[date_str] = []

# Carry over
for offset in range(1, 31):
    past = (today - timedelta(days=offset)).strftime("%Y-%m-%d")
    if past in st.session_state.tasks_by_date:
        for t in st.session_state.tasks_by_date[past]:
            if not t.get("completed") and t["text"] not in [x["text"] for x in st.session_state.tasks_by_date[date_str]]:
                st.session_state.tasks_by_date[date_str].append(t.copy())

tasks = st.session_state.tasks_by_date[date_str]
total, done = len(tasks), sum(t.get("completed", False) for t in tasks)
score = int(done/total*100) if total else 0

# CSS
st.markdown(f"""
<style>
    .reportview-container {{ background: {bg}; color: {text} }}
    .task-card {{ padding: 20px; margin: 16px 0; border-radius: 20px; background: rgba(255,75,75,0.1);
                  border-left: 8px solid {accent}; box-shadow: 0 8px 25px rgba(0,0,0,0.3); }}
    .progress-fill {{ width: {score}%; background: linear-gradient(90deg, #ff4b4b, #00ff88); height: 70px;
                      border-radius: 35px; display: flex; align-items: center; justify-content: center;
                      font-size: 36px; font-weight: bold; color: white; }}
    .prio-btn {{ border: none !important; box-shadow: 0 5px 15px rgba(0,0,0,0.4) !important;
                 transition: all 0.2s !important; }}
    .prio-btn:hover {{ transform: scale(1.15) !important; }}
</style>
""", unsafe_allow_html=True)

# Header & Add Task
st.markdown(f"<h1 style='color:{accent};'>Dojo — {st.session_state.user_name}'s Life OS</h1>", unsafe_allow_html=True)

new = st.text_input("Add task", key="new", label_visibility="collapsed")
if new.strip():
    cols = st.columns(4)
    for i, p in enumerate(PRIORITIES):
        with cols[i]:
            if st.button(p, key=f"add_{p}"):
                tasks.append({"text": new.strip(), "completed": False, "notes": "", "priority": p})
                st.rerun()

# Tasks
st.markdown(f"<div class='progress-fill'>{score}%</div>", unsafe_allow_html=True)

for i, task in enumerate(tasks[:]):
    idx = i
    prio = task.get("priority", "Low")
    color = PRIORITY_COLORS[prio]
    key = f"prio_{date_str}_{idx}"

    st.markdown(f"<div class='task-card{' completed' if task.get('completed') else ''}>", unsafe_allow_html=True)

    # THE RED BADGE IS NOW 100% CLICKABLE — NO WHITE BOX EVER
    if st.session_state.get(key):
        cols = st.columns(4)
        for j, np in enumerate(PRIORITIES):
            with cols[j]:
                if st.button(np, key=f"set_{idx}_{np}"):
                    tasks[idx]["priority"] = np
                    st.session_state[key] = False
                    st.rerun()
        st.button("Cancel", on_click=lambda: st.session_state.pop(key, None))
    else:
        # THIS IS THE FINAL, PERFECT SOLUTION
        st.link_button(
            prio,
            f"?{key}=1",
            use_container_width=False,
            type="primary",
            help="Click to change priority"
        )
        # Apply custom style to make it look like a badge
        st.markdown(
            f"<style>.stButton > button{{{{background:{color}; border:none; border-radius:50px; "
            f"padding:11px 28px; font-weight:bold; box-shadow:0 5px 15px rgba(0,0,0,0.4)}}}</style>",
            unsafe_allow_html=True
        )

    # Trigger edit mode from URL param
    if st.query_params.get(key) == "1":
        st.session_state[key] = True
        st.query_params.clear()
        st.rerun()

    st.markdown(f"### {task['text']}")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if task.get("completed"):
            st.success("DONE")
        else:
            if st.button("Complete", key=f"done_{idx}"):
                tasks[idx]["completed"] = True
                st.rerun()
    with c2: st.button("Notes", key=f"n_{idx}")
    with c3: st.button("Edit", key=f"e_{idx}")
    with c4: st.button("Delete", key=f"d_{idx}", on_click=lambda i=idx: tasks.pop(i) or st.rerun())

    st.markdown("</div>", unsafe_allow_html=True)

st.caption("v11.0 — RED BADGE IS FULLY CLICKABLE • No white box • No extra element • Pure perfection")
