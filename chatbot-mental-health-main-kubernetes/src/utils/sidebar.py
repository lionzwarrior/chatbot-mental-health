import streamlit as st
from core.connection import Connection
from core.chat_session import ChatSession
from utils.utils import get_cookies
from bson import ObjectId

cookies = get_cookies()
conn = Connection()

def build_sidebar():
    st.markdown(
        """
        <style>
            div [data-testid="stSidebarNav"] {
                display: none
            }
            [data-testid="stSidebarUserContent"] {
                margin-top: 10%;
                padding-top: 10%;
                padding-bottom: 7%;
            }
            [data-testid="stSidebarUserContent"] p {
                padding: 0.45rem 0 0.45rem;
            }
            [data-testid="stSidebarUserContent"] .stButton button[kind="secondary"],  
            div[aria-haspopup="true"] button[kind="secondary"]{
                height: 0;
                width: 100%;
                background-color: #ADEBED;
            }
            div[aria-haspopup="true"] button[kind="secondary"] div[data-testid="stMarkdownContainer"] {
                width: 80%;
            }
            [data-testid="stSidebarUserContent"] .stSelectbox label {
                display: None;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )
    
    with st.sidebar:
        with st.container():
            st.image("asset/PCU.png")
            with st.container():
                st.write("Language")
                if cookies.get("language") is None:
                    cookies["language"] = "IND"

                language_list = ["IND", "ENG"]
                language = st.selectbox("Language", language_list, index=language_list.index(cookies["language"]), label_visibility="hidden")
                
                if language and language != cookies.get("language"):
                    cookies["language"] = language

            st.page_link("app.py", label="🏠 Home")
            st.page_link("pages/profile.py", label="👤 {}".format(conn.find_user({"_id": ObjectId(st.session_state.user["_id"])})["username"]))

        chat_session()
        logout = st.button("Log out")
    
        if logout:
            del st.session_state.user
            del cookies["user"]
            st.switch_page("pages/authentication.py")

        with st.container(border=True):
            st.markdown("""Chatbot might make mistakse, please do not hesitate to reach out Pusat Konseling dan Pengembangan Pribadi 
            (PKPP) at:
            \n📍 Universitas Kristen Petra, Gedung D.111, Jl. Siwalankerto 121-131, Surabaya
            \n🕛 Senin - Jumat, 07.30 - 15.30 WIB
            \n📱 +62 895-2330-5960
            \n🌐 https://pkpp.petra.ac.id/""")

def chat_session():
    chat_sessions = [session for session in conn.retrieve_user_chat_sessions(conn.find_user({"_id": ObjectId(st.session_state.user["_id"])})["username"])]
    session_button = []
    if len(chat_sessions) != 0:
        st.write("#### Chat Sessions:")
        with st.container(height=175):
            for i, session in enumerate(chat_sessions):
                session_button.append(st.button(session["title"], key=f"session_btn_{i}"))



        if True in session_button:
            index = session_button.index(True)
            filter = {"_id": chat_sessions[index]["_id"],
                      "user": st.session_state.user["username"],
                      "creation_time": chat_sessions[index]["creation_time"]}
            settings = conn.find_chat_session(filter)
            st.session_state.chat_session = ChatSession(settings)
            st.switch_page("pages/chat.py")