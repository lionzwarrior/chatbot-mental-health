import streamlit as st
from utils.sidebar import build_sidebar
from core.chatbot import Chatbot
from core.chat_session import ChatSession
from utils.utils import get_cookies

import time
import json

cookies = get_cookies()

# Styling
st.markdown(
        """
        <style>
            .st-emotion-cache-1ru4d5d {
                padding-top: 3rem;
            }
            div[data-testid="stVerticalBlock"] div:has(div.fixed-header) {
                position: sticky;
                top:1.5rem;
                background-color: #FDFDFD;
                z-index: 999;
            }
            .fixed-header {
                border-bottom: 1px solid gray;
            }
            [data-testid="stAppViewBlockContainer"] button[kind="secondary"] {
                margin-top: 1.75rem;
                border: none;
                width: 100%;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

# Main Program
if "start_time" not in st.session_state:
    st.session_state.start_time = None

if "user" not in cookies or not cookies["user"]:
    st.switch_page("pages/authentication.py")
else:
    st.session_state.user = json.loads(cookies["user"])
    st.session_state.chatbot = Chatbot(cookies["chatbot"])
    # Sidebar
    build_sidebar()

    # Initialize chat session
    if "chat_session" not in st.session_state:
        if "chatbot" not in st.session_state:
            st.session_state.chatbot = Chatbot()
        st.session_state.chat_session = ChatSession(st.session_state.user["username"], st.session_state.chatbot)
        st.session_state.chat_session.chat(
                {"role": "assistant", 
                 "content": "Hello there 👋!\n\n Good to see you, how may I help you today 😁?"}
            )
        st.rerun()
    else:
        chatbot_settings = st.session_state.chat_session.chatbot
        chatbot = Chatbot(chatbot_settings["llm"], chatbot_settings["embedding_model"], chatbot_settings["vector_store"])
        st.session_state.chatbot = chatbot

    if "disabled" not in st.session_state:
        st.session_state.disabled = False

    chat_session = st.session_state.chat_session

    # Prompt for user input and save to chat history
    if prompt := st.chat_input("Your question", disabled=st.session_state.disabled):
        st.session_state.start_time = time.time()
        chat_session.chat({"role": "user", "content": prompt})
        # st.session_state.disabled = True
        # st.rerun()

    # Display chat history on app rerun
    messages = chat_session.get_chat_history()

    # Chat Title & Editing
    if "editing_title" not in st.session_state:
        st.session_state.editing_title = False

    header = st.container()
    with header:
        col1, col2 = st.columns([9,1])
        with col1:
            title = st.empty()
            title.header(chat_session.title)
        with col2:
            edit = st.empty()
            edit_button = edit.button("✏️", key="edit")
        if edit_button or st.session_state.editing_title:
            st.session_state.editing_title = True
            new_title = title.text_input("Title:", value=chat_session.title, label_visibility="hidden")
            save = edit.button("Save")
            if save:
                with st.spinner("Loading..."):
                    title.header(new_title)
                    del save
                    chat_session.update_title(new_title)
                    st.session_state.editing_title = False
                    st.rerun()

        header.markdown("""<div class='fixed-header' />""", unsafe_allow_html=True)

    # Set variable
    chatbot = st.session_state.chatbot
    chatbot.set_chat_history(messages)
    print(chatbot.chat_history)
    print("\n", chatbot.chat_store)
    print("\n", chatbot.memory)

    for message in messages:
        with st.chat_message(message["role"]):
            with st.container():
                col1, col2 = st.columns([7, 3])
                with col1:
                    if message["role"] == "user":
                        st.markdown(f"##### {st.session_state.user['username']}")
                    else:
                        st.markdown(f"##### Counsel@PCU-Bot - {chat_session.chatbot['llm']}")
                with col2:
                    st.markdown(message["time"])
            st.markdown(message["content"])

    # If last message is not from assistant, generate a new response
    if messages[-1]["role"] != "assistant":
        with st.chat_message("assistant"):
            with st.container():
                col1, col2 = st.columns([7, 3])
                with col1:
                    st.markdown(f"##### Counsel@PCU-Bot - {chat_session.chatbot['llm']}")
                with col2:
                    st.markdown(message["time"])
            response = st.write_stream(chatbot.stream_response_generator(prompt))
            message = {"role": "assistant", "content": response}
            # Add response to message history
            chat_session.chat({"role": message["role"], "content": message["content"]})
            # st.session_state.disabled = False
            end_time = time.time()
            total_time = end_time - st.session_state.start_time
            with open("http_latency.log", "a") as f:
                f.write(f"Total WebSocket Latency: {total_time:.2f} sec\n")
            # st.rerun()
