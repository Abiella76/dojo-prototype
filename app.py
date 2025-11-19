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

# Initialize session state early with defaults
@st.cache_data(ttl=3600)  # Cache for 1 hour, but session persists across reruns
def load_data():
    defaults = {
        'tasks': [],
        'points': 0,
        'streak': 0,
        'last_date': datetime.now().date(),
        'ai_history': []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    return st.session_state

def save_data(data):
    st.session_state.update(data)

def check_carryover():
    # Extra safe: Ensure keys exist before access
    load_data()  # Re-ensure init
    today = datetime.now().date()
    last_date = st.session_state.get('last_date', datetime.now().date() - timedelta(days=1))
    
    if last_date != today:
        # Carry over unfinished tasks
        unfinished = [t for t in st.session_state.tasks if not t['completed']]
        st.session_state.tasks = unfinished  # For now, no 'new_tasks' yet
        # Update streak: +1 if any tasks (finished or not), reset if empty day
        if st.session_state.tasks or unfinished:
            st.session_state.streak += 1
        else:
            st.session_state.streak = 0
        st.session_state.last_date = today
        save_data(st.session_state)
        st.rerun()  # Refresh to show updates

def calculate_score(tasks):
    total = len(tasks)
    completed = sum(1 for t in tasks if t['completed'])
    return (completed / total * 100) if total > 0 else 0

def get_ai_response(user_input, tasks):
    # Simple mock: Analyze tasks for suggestions
    task_text = ' '.join([t['text'] for t in tasks]).lower()
    if 'fitness' not in task_text and 'workout' not in task_text and 'exercise' not in task_text:
        return "Quick nudge: No fitness today? Add a 5-min stretch for balance! What's your take?"
    return random.choice(AI_RESPONSES)

# Main App - Load data EARLY
st.set_page_config(page_title="Dojo Prototype", page_icon="🥋", layout="wide")
load_data()  # Initialize before anything else
st.title("🥋 Dojo: Your Nightly Productivity Ritual")

data = st.session_state  # Reference directly now
check_carryover()  # Safe to call now

# Sidebar: AI Companion
with st.sidebar:
    st.header("🤖 Your AI Dojo Master")
    if data.ai_history:
        for msg in data.ai_history[-5:]:  # Last 5 exchanges
            with st.chat_message("user" if msg['role'] == 'user' else "assistant"):
                st.write(msg['content'])
    
    if prompt := st.chat_input("Chat with your AI coach... (e.g., 'Suggest a task')"):
        data.ai_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        response = get_ai_response(prompt, data.tasks)
        data.ai_history.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.write(response)
        st.rerun()

    st.markdown("---")
    st.metric("Total Points", data.points)
    st.metric("Streak", f"{data.streak} days")

# Main Content: Two Columns for Desktop/Mobile
col1, col2 = st.columns([2, 1])

with col1:
    tomorrow_date = datetime.now().date() + timedelta(days=1)
    st.subheader(f"📋 Tomorrow's Dojo ({tomorrow_date})")
    
    # Add task
    with st.form("add_task"):
        task_text = st.text_input("New task:", placeholder="e.g., Finish report, Gym session")
        if st.form_submit_button("Add Task"):
            data.tasks.append({"text": task_text, "completed": False})
            save_data(data)
            st.success(f"Added: {task_text}")
            st.rerun()
    
    # Task list
    score = calculate_score(data.tasks)
    st.metric("Daily Score", f"{score:.0f}%", delta=f"{score-80:+.0f}" if score > 0 else None)
    
    # Render tasks with checkboxes (use keys for state)
    for i, task in enumerate(data.tasks):
        if st.checkbox(task['text'], key=f"task_cb_{i}", value=task['completed']):
            if not task['completed']:  # Just completed now
                data.points += 10
                task['completed'] = True
                save_data(data)
                st.balloons()  # Fun confetti!
        col_check, col_delete = st.columns([1, 1])
        with col_check:
            if st.button("✓", key=f"check_{i}", disabled=task['completed']):
                data.points += 10
                task['completed'] = True
                save_data(data)
                st.rerun()
        with col_delete:
            if st.button("🗑️", key=f"del_{i}"):
                del data.tasks[i]
                save_data(data)
                st.rerun()

with col2:
    st.subheader("Quick Stats")
    unfinished_count = len([t for t in data.tasks if not t['completed']])
    st.write(f"**Tasks left:** {unfinished_count}")
    if st.button("End Day & Carry Over"):
        check_carryover()
        st.success("Day closed! Unfinished tasks rolled to tomorrow. 💪")
    st.markdown("---")
    if st.button("Reset Streak (for testing)"):
        data.streak = 0
        save_data(data)
        st.rerun()

# Footer
st.markdown("---")
st.caption("Built with ❤️ by Grok & Abi. Night plan → Crush day → Level up. Repeat.")

# Auto-save button
if st.button("Save & Sync"):
    save_data(data)
    st.success("Saved! (Persists in browser—refresh to test carry-over.)")
