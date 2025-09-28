import os
import streamlit as st
import datetime

from streamlit_cookies_manager import EncryptedCookieManager

from utils.sidebar import build_sidebar
from core.chatbot import Chatbot

secret = os.getenv("COOKIE_SECRET", "your_very_secret_key")
cookies = EncryptedCookieManager(password=secret)

if not cookies.ready():
    st.stop()

# Main Program
st.session_state.user = {"username": "test", "role": "admin", "assessment": ""}
st.session_state.chatbot = Chatbot()

st.title("Counsel@PCU-Bot (Versi Percobaan)")

# Sidebar
build_sidebar(cookies)

if "chatbot" not in st.session_state:
    st.warning("Please configure your chatbot first!")
else:
    chatbot = st.session_state.chatbot

    if "disabled" not in st.session_state:
        st.session_state.disabled = False

    # Initialize chat history
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": "Hello there 👋!\n\n Good to see you, how may I help you today 😁?",
                "time": datetime.datetime.now().strftime("%Y/%m/%d %H:%M"),
            }
        ]

    # Prompt for user input and save to chat history
    if prompt := st.chat_input("Your question", disabled=st.session_state.disabled):
        st.session_state.chat_messages.append(
            {
                "role": "user",
                "content": prompt,
                "time": datetime.datetime.now().strftime("%Y/%m/%d %H:%M"),
            }
        )
        st.session_state.disabled = True
        print(chatbot.chat_store)

    # Display chat messages from history on app rerun
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            with st.container():
                col1, col2 = st.columns([8, 2])
                with col1:
                    st.markdown(f'##### {message["role"]}')
                with col2:
                    st.markdown(message["time"])
            st.markdown(message["content"])

    # If last message is not from assistant, generate a new response
    if st.session_state.chat_messages[-1]["role"] != "assistant":
        with st.chat_message("assistant"):
            st.markdown("##### assistant")
            response = st.write_stream(chatbot.stream_response_generator(prompt))
            message = {
                "role": "assistant",
                "content": response,
                "time": datetime.datetime.now().strftime("%Y/%m/%d %H:%M"),
            }
            # Add response to message history
            st.session_state.chat_messages.append(message)
            st.session_state.disabled = False
