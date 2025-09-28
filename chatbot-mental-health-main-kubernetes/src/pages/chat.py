import os
import streamlit as st
import time
import json

from datetime import datetime, timedelta, timezone

from streamlit_cookies_manager import EncryptedCookieManager
from utils.sidebar import build_sidebar
from core.chatbot import Chatbot, get_first_available_model
from core.chat_session import ChatSession
from utils.metrics import inc_concurrent_requests, dec_concurrent_requests

secret = os.getenv("COOKIE_SECRET", "your_very_secret_key")
cookies = EncryptedCookieManager(password=secret)

if not cookies.ready():
    st.stop()


st.markdown(
    """
    <style>
        .st-emotion-cache-1ru4d5d {
            padding-top: 3rem;
        }
        div[data-testid="stVerticalBlock"] div:has(div.fixed-header) {
            position: sticky;
            top:1.5rem;
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

tz = timezone(timedelta(hours=7))
LOG_FILE = "total_response_time.log"

if "user" not in cookies or not cookies["user"]:
    st.switch_page("pages/authentication.py")
else:
    if "user" not in st.session_state:
        st.session_state.user = json.loads(cookies["user"])

    @st.cache_resource
    def load_global_chatbot_instance(
        llm_model: str, embedding_model: str, vector_store: str
    ):
        return Chatbot(
            llm=llm_model, embedding_model=embedding_model, vector_store=vector_store, user_id=st.session_state.user["_id"]
        )

    build_sidebar(cookies)
    
    if "chatbot" not in st.session_state:
        if (
            ("chatbot" in cookies and cookies["chatbot"])
            and ("embedding" in cookies and cookies["embedding"])
            and ("vector_store" in cookies and cookies["vector_store"])
        ):
            try:
                initial_chatbot_config = cookies["chatbot"]
                initial_embedding_config = cookies["embedding"]
                initial_vector_store_config = cookies["vector_store"]
                st.session_state.chatbot = load_global_chatbot_instance(
                    initial_chatbot_config,
                    initial_embedding_config,
                    initial_vector_store_config
                )
            except (json.JSONDecodeError, KeyError) as e:
                st.error(
                    f"Error loading initial chatbot configuration from cookies: {e}"
                )
                st.stop()
        else:
            default_llm = get_first_available_model()
            default_embedding_model = "intfloat/multilingual-e5-large"
            default_vector_store = "Qdrant"

            st.session_state.chatbot = load_global_chatbot_instance(
                default_llm, default_embedding_model, default_vector_store
            )

    if "chat_session" not in st.session_state:
        st.session_state.chat_session = ChatSession(
            st.session_state.user["username"],
            st.session_state.chatbot,
        )
        st.session_state.chat_session.chat(
            {
                "role": "assistant",
                "content": "Hello there 👋!\n\n Good to see you, how may I help you today 😁?",
            }
        )
        st.rerun()
    else:
        if "chatbot" not in st.session_state:
            if (
                ("chatbot" in cookies and cookies["chatbot"])
                and ("embedding" in cookies and cookies["embedding"])
                and ("vector_store" in cookies and cookies["vector_store"])
            ):
                try:
                    initial_chatbot_config = cookies["chatbot"]
                    initial_embedding_config = cookies["embedding"]
                    initial_vector_store_config = cookies["vector_store"]
                    st.session_state.chatbot = load_global_chatbot_instance(
                        initial_chatbot_config,
                        initial_embedding_config,
                        initial_vector_store_config,
                    )
                except (json.JSONDecodeError, KeyError) as e:
                    st.error(
                        f"Error loading initial chatbot configuration from cookies: {e}"
                    )
                    st.stop()
            else:
                default_llm = get_first_available_model()
                default_embedding_model = "intfloat/multilingual-e5-large"
                default_vector_store = "Qdrant"

                st.session_state.chatbot = load_global_chatbot_instance(
                    default_llm, default_embedding_model, default_vector_store
                )

    if "chat_input_disabled" not in st.session_state:
        st.session_state.chat_input_disabled = False

    chat_session = st.session_state.chat_session

    prompt = st.chat_input(
        "Your question", disabled=st.session_state.chat_input_disabled
    )

    if prompt:
        st.session_state.start_time = time.time()
        inc_concurrent_requests()
        chat_session.chat({"role": "user", "content": prompt})
        st.session_state.chat_input_disabled = True
        st.rerun()

    messages = chat_session.get_chat_history()

    if "editing_title" not in st.session_state:
        st.session_state.editing_title = False

    header = st.container()
    with header:
        col1, col2 = st.columns([9, 1])
        with col1:
            title_display_area = st.empty()
            title_display_area.header(chat_session.title)
        with col2:
            edit_button_area = st.empty()
            edit_button = edit_button_area.button("✏️", key="edit")

        if edit_button or st.session_state.editing_title:
            st.session_state.editing_title = True
            new_title = title_display_area.text_input(
                "Title:",
                value=chat_session.title,
                label_visibility="hidden",
                key="title_input",
            )
            save_button = edit_button_area.button("Save", key="save_title")
            if save_button:
                with st.spinner("Saving title..."):
                    chat_session.update_title(new_title)
                    st.session_state.editing_title = False
                    st.rerun()
        header.markdown("""<div class='fixed-header' />""", unsafe_allow_html=True)

    st.session_state.chatbot.set_chat_history(messages)

    for message in messages:
        with st.chat_message(message["role"]):
            with st.container():
                col1, col2 = st.columns([7, 3])
                with col1:
                    if message["role"] == "user":
                        st.markdown(f"##### {st.session_state.user['username']}")
                    else:
                        st.markdown(
                            f"##### Counsel@PCU-Bot - {st.session_state.chatbot.llm}"
                        )

                with col2:
                    st.markdown(message["time"])
            st.markdown(message["content"])

    if messages and messages[-1]["role"] == "user":
        with st.chat_message("assistant"):
            with st.container():
                col1, col2 = st.columns([7, 3])
                with col1:
                    st.markdown(
                        f"##### Counsel@PCU-Bot - {st.session_state.chatbot.llm}"
                    )
                with col2:
                    st.markdown(
                        datetime.now(timezone.utc)
                        .astimezone(tz)
                        .strftime("%Y/%m/%d %H:%M:%S")
                    )

            response_generator = st.session_state.chatbot.stream_response_generator(
                messages[-1]["content"]
            )
            response_content = st.write_stream(response_generator)

            new_assistant_message = {
                "role": "assistant",
                "content": response_content,
                "time": datetime.now(timezone.utc)
                .astimezone(tz)
                .strftime("%Y/%m/%d %H:%M:%S"),
            }
            chat_session.chat(new_assistant_message)

            st.session_state.chat_input_disabled = False
            end_time = time.time()
            total_time = end_time - st.session_state.start_time
            dec_concurrent_requests()
            print(f"Total Response Latency: {total_time:.2f} sec\n")
            with open(LOG_FILE, "a") as f:
                f.write(
                    f"Total Response Time:;{total_time:.4f};seconds;username;{st.session_state.user["username"]}\n"
                )
            st.rerun()
