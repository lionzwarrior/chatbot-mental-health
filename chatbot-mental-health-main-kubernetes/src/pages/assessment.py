import streamlit as st
from utils.sidebar import build_sidebar
from core.chatbot import Chatbot
from core.connection import Connection
from datetime import datetime, timedelta, timezone
from utils.utils import get_cookies
from bson import ObjectId
import json

def generate_result(last_message):
    result_prompt = f"Given this summary about user's mental health {last_message}, make the condensed and summary version of the assessment result for the user's mental health condition only for system information purpose without referring the user and no preamble or explanations. For examples: Good outlook on life, but unhealthy coping ways; Feeling lonely, no support from family & friends, etc. Give the output in dictionary format that includes current_emotional_state, cause, symtomps, and coping_strategies as keys. Make sure that there is no null values. If there is null values, replace it with none or nothing identified."
    assessment_result = chatbot.response_generator(result_prompt)
    return assessment_result

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
            button[kind="secondary"] {
                width: 100%;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

conn = Connection()
cookies = get_cookies()

# Main Program
if "user" not in cookies or not cookies["user"]:
    st.switch_page("pages/authentication.py")
else:
    st.session_state.user = json.loads(cookies["user"])
    header = st.container()
    with header:
        header.title("Assessment")
        header.markdown("""<div class='fixed-header' />""", unsafe_allow_html=True)
    
    # Sidebar
    build_sidebar()

    # Initialize Chatbot
    # if "chatbot" not in st.session_state:
    #     st.session_state.chatbot = Chatbot("openchat:latest")
    # else:
    #     setting = st.session_state.chatbot.get_setting()
    #     st.session_state.chatbot = Chatbot(setting["llm"], setting["embedding_model"], setting["vector_store"])

    st.session_state.chatbot = Chatbot("openchat:latest")
    chatbot = st.session_state.chatbot

    # Initialize chat history
    tz = timezone(timedelta(hours=7))
    
    if "assessment_messages" not in st.session_state:
        assessment_prompt = """You are asked to act as a counselor conducting an assessment regarding my mental health. You will ask me 10 questions in a row
        gradually by asking them one by one. Avoid asking more than 1 question in your conversation response, the next question should only be asked after you get the context of my answer to the previous question. Apart from that, avoid giving your thoughts when asking questions before you draw conclusions at the end of the assessment regarding my mental condition. Now ask just one question and wait for me to answer. After that you give
        second question and wait for me to answer, then third question and wait for me to answer. You continue to do this until the tenth question or the last question. After the last question, you are asked to provide a comprehensive summary about me from the answers I have given that might consist of current emotional state, cause, symtomps, and recommended coping strategies. The question format is:
        Question n:
        (question to be asked)
        """
        response = chatbot.response_generator(assessment_prompt)
        st.session_state.assessment_messages = [
            {"role": "user", 
             "content": f"{assessment_prompt}",
             "time": datetime.now().astimezone(tz).strftime('%Y/%m/%d %H:%M:%S')},
            {"role": "assistant", 
             "content": response,
             "time": datetime.now().astimezone(tz).strftime('%Y/%m/%d %H:%M:%S')},
        ]
    
    # Prompt for user input and save to chat history
    if prompt := st.chat_input("Input message here"):
        st.session_state.assessment_messages.append({"role": "user", "content": prompt,
                                                     "time": datetime.now().astimezone(tz).strftime('%Y/%m/%d %H:%M:%S')})

    # Set variable
    chatbot.set_chat_history(st.session_state.assessment_messages)
    print(chatbot.chat_history)
    print("\n", chatbot.chat_store)
    print("\n", chatbot.memory)
    
    # Display chat messages from history on app rerun
    for i in range(1, len(st.session_state.assessment_messages)):
        message = st.session_state.assessment_messages[i]
        with st.chat_message(message["role"]):
            with st.container():
                col1, col2 = st.columns([7, 3])
                with col1:
                    if message["role"] == "user":
                        st.markdown(f"##### {st.session_state.user['username']}")
                    else:
                        st.markdown(f"##### Counsel@PCU-Bot - {chatbot.llm}")
                with col2:
                    st.markdown(message["time"])
            st.markdown(message["content"])
    
    # If last message is not from assistant, generate a new response
    if st.session_state.assessment_messages[-1]["role"] != "assistant":
        with st.chat_message("assistant"):
            with st.container():
                col1, col2 = st.columns([7, 3])
                with col1:
                    st.markdown(f"##### Counsel@PCU-Bot - {chatbot.llm}")
                with col2:
                    st.markdown(message["time"])
            response = st.write_stream(chatbot.stream_response_generator(prompt))
            message = {"role": "assistant", "content": response,
                       "time": datetime.now().astimezone(tz).strftime('%Y/%m/%d %H:%M:%S')}
            # Add response to message history
            st.session_state.assessment_messages.append(message)

    # Check if last message is the summary
    last_message = st.session_state.assessment_messages[-1]
    if "Question " not in last_message["content"] and last_message["role"] == "assistant":
        assessment_result = generate_result(last_message['content'])
        col1, col2 = st.columns(2)
        with col1:
            save = st.button("Save Result 💾")
        with col2:
            retry = st.button("Re-take Assessment 📝")
        if save:
            try:
                assessment_dict = eval(assessment_result)
                # Update to DB
                filter = {"_id": ObjectId(st.session_state.user["_id"]), "username": st.session_state.user["username"]}
                conn.update_user(filter, {"$set": {"assessment": assessment_dict}})
                # st.session_state.user["assessment"] = conn.find_user(filter)["assessment"]
                st.success("Successfully saving assessment result!")
            except Exception as e:
                st.warning("Error saving assessment result, please try again!")
                st.rerun()
        elif retry:
            del st.session_state.assessment_messages
            st.rerun()