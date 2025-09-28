import os
import streamlit as st
import json
import threading

from streamlit_cookies_manager import EncryptedCookieManager

st.set_page_config(initial_sidebar_state="expanded")

from core.chatbot import get_first_available_model
from utils.sidebar import build_sidebar
from utils.metrics import start_metrics_server, count_request

secret = os.getenv("COOKIE_SECRET", "your_very_secret_key")
cookies = EncryptedCookieManager(password=secret)

if not cookies.ready():
    st.stop()

if "metrics_server_thread" not in st.session_state:
    metrics_thread = threading.Thread(
        target=start_metrics_server, args=(8000,), daemon=True
    )
    metrics_thread.start()
    st.session_state["metrics_server_thread"] = metrics_thread
    print("Metrics server thread initialized and started.")


# Styling
st.markdown(
    """
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
            """,
    unsafe_allow_html=True,
)


# Main Program
if "user" not in cookies or not cookies["user"]:
    st.switch_page("pages/authentication.py")
else:
    st.session_state.user = json.loads(cookies["user"])
    count_request()
    st.title("Counsel@PCU-Bot (Testing Development)")

    # Sidebar
    build_sidebar(cookies)
    
    if "chatbot" not in cookies or not cookies["chatbot"]:
        cookies["chatbot"] = get_first_available_model()
        cookies.save()
        
    if "embedding" not in cookies or not cookies["embedding"]:
        cookies["embedding"] = "intfloat/multilingual-e5-large"
        cookies.save()
        
    if "vector_store" not in cookies or not cookies["vector_store"]:        
        cookies["vector_store"] = "Qdrant"
        cookies.save()

    # Initialize chat history
    with st.chat_message("assistant"):
        st.markdown("##### Counsel@PCU-Bot")
        st.markdown(
            """Hello there 👋!\n\n Good to see you, how may I help you today 😁? Do you want to take the assessment? 
                    Or maybe we can just talk about how you feel?"""
        )

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
