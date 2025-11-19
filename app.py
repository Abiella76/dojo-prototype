import streamlit as st
import json
from datetime import datetime, timedelta
import random

# Mock AI responses (we'll replace with real Grok API later)
AI_RESPONSES = [
    "Sounds like a solid plan! That'll get your momentum rolling. What's the win feel like for you?",
    "Love it—small steps to mastery. Need any quick tips on that one?",
    "You're building a streak here. Pro tip: Tackle the toughest first for that dopamine rush.",
    "Balanced list—personal growth + work? You're leveling up fast!",
    "Fitness gap spotted? How about adding '10-min walk' to keep the energy high?",
    "Crushed it yesterday! What's one thing you're most excited to check off today?"
]

@st.cache_data(ttl=3600)  # Cache for 1 hour, but we'll use session state for persistence
def load_data():
    if 'tasks' not in st.session_state:
        st.session_state.tasks = []
    if 'points' not in st.session_state:
        st.session_state.points = 0
    if 'streak' not in st.session_state:
        st.session_state.streak = 0
    if 'last_date' not in st.session_state:
        st.session_state.last_date = datetime.now().date()
    if 'ai_history' not in st.session_state:
        st.session_state.ai_history = []
    return st.session_state

def save_data(data):
    st.session_state.update(data)

def check_carryover():
    today = datetime.now().date()
    if st.session_state.last_date != today:
        # Carry over unfinished tasks
        unfinished = [t for t in st.session_state.tasks if not t['completed']]
        st.session_state.tasks = unfinished + st.session_state.new_tasks if 'new_tasks' in st.session_state else unfinished
        # Update streak
        if unfinished or st.session_state.tasks:
            st.session_state.streak += 1
        else:
            st.session_state.streak = 0
        st.session_state.last_date = today
        save_data(st.session_state)

def calculate_score(tasks):
    total = len(tasks)
    completed = sum(1 for t in tasks if t['completed'])
    return (completed / total * 100) if total > 0 else 0

def get_ai_response(user_input, tasks):
    # Simple mock: Analyze tasks for suggestions
    if 'fitness' not in ' '.join([t['text'] for t in tasks]).lower():
        return "Quick nudge: No fitness today? Add a 5-min stretch for balance! What's your take?"
    return random.choice(AI_RESPONSES)

# Main App
st.set_page_config(page_title="Dojo Prototype", page_icon="🥋", layout="wide")
st.title("🥋 Dojo: Your Nightly Productivity Ritual")

data = load_data()
check_carryover()

# Sidebar: AI Companion
with st.sidebar:
    st.header("🤖 Your AI Dojo Master")
    if st.session_state.ai_history:
        for msg in st.session_state.ai_history[-5:]:  # Last 5 exchanges
            with st.chat_message("user" if msg['role'] == 'user' else "assistant"):
                st.write(msg['content'])
    
    if prompt := st.chat_input("Chat with your AI coach... (e.g., 'Suggest a task')"):
        st.session_state.ai_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        response = get_ai_response(prompt, data.tasks)
        st.session_state.ai_history.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.write(response)
        st.rerun()

    st.markdown("---")
    st.metric("Total Points", data.points)
    st.metric("Streak", f"{data.streak} days")

# Main Content: Two Columns for Desktop/Mobile
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"📋 Tomorrow's Dojo ({datetime.now().date() + timedelta(days=1)})")
    
    # Add task
    with st.form("add_task"):
        task_text = st.text_input("New task:", placeholder="e.g., Finish report, Gym session")
        if st.form_submit_button("Add Task"):
            data.tasks.append({"text": task_text, "completed": False})
            save_data(data)
            st.rerun()
    
    # Task list
    score = calculate_score(data.tasks)
    st.metric("Daily Score", f"{score:.0f}%", delta=f"{score-80:+.0f}" if score > 0 else None)
    
    for i, task in enumerate(data.tasks):
        col_task, col_check, col_delete = st.columns([3, 1, 1])
        with col_task:
            st.checkbox(task['text'], key=f"task_{i}", value=task['completed'],
                        on_change=lambda idx=i: toggle_task(idx))
        with col_check:
            if st.button("✓", key=f"check_{i}", disabled=task['completed']):
                toggle_task(i)
        with col_delete:
            if st.button("🗑️", key=f"del_{i}"):
                del data.tasks[i]
                save_data(data)
                st.rerun()

def toggle_task(idx):
    data.tasks[idx]['completed'] = not data.tasks[idx]['completed']
    if data.tasks[idx]['completed']:
        data.points += 10
    save_data(data)
    st.rerun()

with col2:
    st.subheader("Quick Stats")
    st.write(f"**Tasks:** {len([t for t in data.tasks if not t['completed']])} left")
    if st.button("End Day & Carry Over"):
        check_carryover()
        st.success("Day closed! Unfinished tasks rolled to tomorrow.")
        st.rerun()
    st.markdown("---")
    if st.button("Reset Streak (for testing)"):
        data.streak = 0
        save_data(data)
        st.rerun()

# Footer
st.markdown("---")
st.caption("Built with ❤️ by Grok & Abi. Night plan → Crush day → Level up. Repeat.")

# Auto-save on change
if st.button("Save & Sync"):
    save_data(data)
    st.success("Saved! Refresh to see on other devices.")
