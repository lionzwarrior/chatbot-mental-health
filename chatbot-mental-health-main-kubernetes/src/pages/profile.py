import streamlit as st
import time
import ollama
import json

from core.chatbot import Chatbot
from utils.sidebar import build_sidebar
from pages.authentication import hash_pass, validate_pass
from core.connection import Connection
from utils.utils import get_cookies
from bson import ObjectId

from streamlit_modal import Modal

conn = Connection()
cookies = get_cookies()

def update_pass(password, filter):
    new_pass = hash_pass(password)
    return conn.update_user(filter, {"$set": {"password": new_pass}})


def change_password():
    with st.expander("Change Password?"):
        current_pass = st.text_input("Current Password: ", type="password")
        new_pass = st.text_input("New Password: ", type="password")
        match_pass = st.text_input("Re-type New Password: ", type="password")
        submitted = st.button("Save")

    if submitted:
        if validate_pass(current_pass.strip(), conn.find_user({"_id": ObjectId(st.session_state.user["_id"])})["password"]):
            if new_pass.strip() != match_pass.strip():
                st.error("New password don't match each other, check your input!")
            elif " " in new_pass.strip():
                st.warning("Whitespace is not allowed!")
            else:
                filter = {"_id": ObjectId(st.session_state.user["_id"])}
                update_pass(new_pass.strip(), filter)
                st.success("Successfully changed the password!")
                time.sleep(3)
                st.switch_page("pages/authentication.py")
        else:
            st.error("Current password is incorrect, try again!")


def account_profile():
    st.header("Account")
    col1, col2 = st.columns(2)
    for key in st.session_state.user:
        with st.container():
            col1, col2 = st.columns(2)
            with col1:
                if key not in ["_id", "password", "assessment"]:
                    st.write(key.capitalize())
            with col2:
                if key not in ["_id", "password", "assessment"]:
                    st.write(st.session_state.user[key])
    # Change Pass
    change_password()

    st.header("Assesment")
    if conn.find_user({"_id": ObjectId(st.session_state.user["_id"])})["assessment"] == "":
        st.write("```No assessment yet```")
        assessment_button = st.button("Take Assessment 📝")
    else:
        assessment = st.session_state.user["assessment"]
        keys = ["Current emotional state", "Cause",
                "Symptoms", "Coping strategies"]
        for i, key in enumerate(assessment):
            with st.container():
                col1, col2 = st.columns(2)
                with col1:
                    st.write(keys[i])
                with col2:
                    st.write("".join(assessment[key]).capitalize())
        st.write("")
        assessment_button = st.button("Re-take Assessment 📝")

    if assessment_button:
        st.switch_page("pages/assessment.py")


def chat_management():
    st.header("Chat Session List")
    delete_button = []
    session_list = [session for session in conn.retrieve_user_chat_sessions(
        st.session_state.user["username"])]
    st.warning("Changes will take effect immediately!")
    if len(session_list) > 0:
        for i, session in enumerate(session_list):
            with st.container(border=True):
                col1, col2, col3 = st.columns([5, 3.5, 1.5])
                with col1:
                    st.write(f"💬 {session['title']}")
                with col2:
                    st.write(session["creation_time"])
                with col3:
                    delete = st.button("Delete", key="delete"+str(i))
                    delete_button.append(delete)
    else:
        st.write("`No Chat Session Yet`")

    if True in delete_button:
        index = delete_button.index(True)
        conn.delete_chat_session(
            {"_id": session_list[index]["_id"], "user": st.session_state.user["username"]})
        st.toast(
            f"Successfully deleted {session_list[index]['title']}", icon="❌")
        del session_list[index]
        st.rerun()


def user_management():
    st.header("User List")
    users = conn.retrieve_all_user()
    roles = ["user", "admin"]
    user_role = {}
    user_list = {}
    detail_button = []
    delete_button = []

    st.warning("Changes will take effect immediately!")
    for i, x in enumerate(users):
        disable = False
        user_list[i] = x
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 5, 2.5, 1.5])
            with col1:
                st.write(x["username"])
            with col2:
                st.write(x["email"])
            with col3:
                if x["username"] == st.session_state.user["username"]:
                    disable = True

                role = st.selectbox(label="role",
                                    options=[
                                        x["role"]] + [role for role in roles if role != x["role"]],
                                    label_visibility="hidden", disabled=disable,
                                    key=i)
                user_role[x["username"]] = role
            with col4:
                subcol1, subcol2 = st.columns(2)
                with subcol1:
                    detail = st.button("🛈", key="details"+str(i))
                    detail_button.append(detail)
                with subcol2:
                    delete = st.button("🗑️", key="deletes"+str(i))
                    delete_button.append(delete)

    modal = Modal(key="detailModal", title="User Details",
                  padding=25, max_width=500)
    if True in detail_button:
        i = detail_button.index(True)
        with modal.container():
            user = user_list[i]
            col1, col2 = st.columns(2)
            for key in user.keys():
                if key not in ["_id", "password", "assessment"]:
                    with col1:
                        st.write(key.capitalize())
                    with col2:
                        st.write(user[key])

    if True in delete_button:
        i = delete_button.index(True)
        user = user_list[i]
        if user["role"] != "admin":
            print(user)
            filter = {"_id": user["_id"],
                      "username": user["username"],
                      "email": user["email"]}
            conn.delete_user(filter)
            st.rerun()
        else:
            st.warning("Cannot delete user with admin role!")

    st.write("---")
    with st.expander("Assign New Password", expanded=True):
        username = st.text_input("Username:")
        password = st.text_input("New Password:", type="password")
        save = st.button("Save", key="save")
    if save:
        filter = {"username": username.strip()}
        if " " not in password:
            if update_pass(password.strip(), filter):
                st.success("Successfully changed the password!")
            else:
                st.error("There is no user with name {}".format(username))
        else:
            st.warning("Whitespace is not allowed!")

    change_role(user_role)


def settings_panel():
    if st.session_state.user["role"] == "admin":
        st.header("Knowledge Base")
        knowledge = st.button("📂 Manage Knowledge Base Here")
        if knowledge:
            st.switch_page("pages/upload.py")
    config()
    st.header("Prompt Injection (Coming Soon)")
    st.text_area("Prompt:")


def config():
    ollama_client = ollama.Client(host=st.secrets["ollama"]["url"][st.secrets["ollama"]["models"].index(cookies["chatbot"])])

    st.title("Configuration")

    if "chatbot" not in st.session_state:
        # st.warning("Please configure your chatbot first!")
        st.session_state.chatbot = Chatbot()
    else:
        chatbot = st.session_state.chatbot
        current_settings = {
            "model": chatbot.llm, "embedding": chatbot.embedding_model, "vector_store": chatbot.vector_store}
        print(current_settings)

        model = st.selectbox(
                    "Model:",
                    st.secrets["ollama"]["models"],
                    key="model"
                )


        embedding = st.selectbox("Embedding Model:",
                                 ["intfloat/multilingual-e5-large"],
                                 key="embedding"
                                 )

        vector_store = st.selectbox("Vector Store:",
                                    ["Qdrant"],
                                    key="vector_store"
                                    )

        save_button = st.button("Save Configuration")

        if save_button:
            cookies["chatbot"] = model
            st.session_state.chatbot = Chatbot(model, embedding, vector_store)
            st.success("Successfully configuring chatbot!!!")
            time.sleep(3)
            st.switch_page("app.py")


def change_role(user_role):
    for username, role in user_role.items():
        filter = {"username": username}
        conn.update_user(filter, {"$set": {"role": role}})


# Styling
st.markdown(
    """
<style>
    div[data-modal-container='true'][key='detailModal'] > div:first-child > div:first-child {
        margin-top: -45px !important;
    }
    [data-testid="stAppViewBlockContainer"] {
        padding-top: 0;
        padding-left: 0;
        padding-right: 0;
    }
    [role="tabpanel"] {
        padding-left: 1rem;
        padding-right: 1rem;
    }
    button[role="tab"] {
        width: 100% !important;
    }
    .stSelectbox [data-testid="stWidgetLabel"] {
        display: none;
    }
    p {
        padding: 0.45rem 0 0.45rem;
    }
    button[kind="secondary"] {
        height: 0;
        width: 100%;
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
    build_sidebar()

    if st.session_state.user["role"] == "admin":
        tab1, tab2, tab3, tab4 = st.tabs(
            ["Profile", "Chat Management", "User Management", "Admin Panel"])
        with tab1:
            account_profile()
        with tab2:
            chat_management()
        with tab3:
            user_management()
        with tab4:
            settings_panel()
    else:
        tab1, tab2, tab3 = st.tabs(
            ["Profile", "Chat Management", "User Panel"])
        with tab1:
            account_profile()
        with tab2:
            chat_management()
        with tab3:
            settings_panel()
