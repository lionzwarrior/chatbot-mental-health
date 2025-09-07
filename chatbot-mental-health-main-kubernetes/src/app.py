import streamlit as st
import json
import threading

st.set_page_config(initial_sidebar_state="auto")

from utils.sidebar import build_sidebar
from utils.utils import get_cookies
from utils.metrics import start_metrics_server

if "metrics_server_thread" not in st.session_state:
    metrics_thread = threading.Thread(target=start_metrics_server, args=(8000,), daemon=True)
    metrics_thread.start()
    st.session_state["metrics_server_thread"] = metrics_thread
    print("Metrics server thread initialized and started.")


cookies = get_cookies()

if not cookies.ready():
    st.info("Waiting for cookies to be ready...")
    st.stop() 

# Styling
st.markdown("""
            <style>
                div[data-testid="column"] {
                    width: fit-content !important;
                    flex: unset;
                }
                div[data-testid="column"] * {
                    width: fit-content !important;
                }
                div[data-testid="stHorizontalBlock"] {
                    margin-left: 55px;
                }
                button[kind="secondary"] {
                    background-color: #ADEBED;
                }
            </style>
            """, unsafe_allow_html=True)


# Main Program
if "user" not in cookies or not cookies["user"]:
    st.switch_page("pages/authentication.py")
else:
    st.session_state.user = json.loads(cookies["user"])
    
    st.title("Counsel@PCU-Bot (Testing Development)")

    # Sidebar
    build_sidebar()

    # Initialize chat history
    with st.chat_message("assistant"):
        st.markdown("##### Counsel@PCU-Bot")
        st.markdown("""Hello there 👋!\n\n Good to see you, how may I help you today 😁? Do you want to take the assessment? 
                    Or maybe we can just talk about how you feel?""")
    
    col1, col2 = st.columns(2)
    with col1:
        yes_button = st.button("Yes, I want to take it first! 📝")
    with col2:
        no_button = st.button("No, let's just chat immediately 💬")
    
    if yes_button:
        st.switch_page("pages/assessment.py")
    elif no_button:
        if "chat_session" in st.session_state:
            del st.session_state["chat_session"]
        st.switch_page("pages/chat.py")