import streamlit as st
from datetime import datetime, timedelta
import random
import os
import json
import requests

# ────── SAFE SESSION STATE INIT ──────
defaults = {
    "tasks": [], "points": 0, "streak": 0,
    "last_date": datetime.now().date(),
    "ai_history": [], "user_name": "there"
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ────── GROK API SETUP ──────
GROK_API_KEY = st.secrets.get("GROK_API_KEY") if st.secrets else os.getenv("GROK_API_KEY")

with st.sidebar:
    api_key = st.text_input("Grok API Key (paste here for smart AI)", type="password", key="api_key_input")
    if api_key:
        st.session_state.grok
