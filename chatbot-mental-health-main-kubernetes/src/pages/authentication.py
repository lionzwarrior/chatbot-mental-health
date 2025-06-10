import streamlit as st
from core.connection import Connection
import re
import bcrypt
from utils.utils import get_cookies
import json

def validate_email(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    if(re.fullmatch(regex, email)):
        return True
    else:
        return False


def hash_pass(password):
    # Adding the salt to password
    salt = bcrypt.gensalt()
    
    # Hashing the password
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()


def validate_pass(input, password):
    return bcrypt.checkpw(input.encode(), password.encode())


conn = Connection()
cookies = get_cookies()

# Hide Sidebar
st.set_page_config(initial_sidebar_state="collapsed")

# Styling
st.markdown(
    """
<style>
    [data-testid="collapsedControl"] {
        display: none;
    }

    button[role="tab"] {
        width: 100% !important;
    }

    .row-widget.stButton {
        display: flex;
        justify-content: center;
    }

    button[data-testid="baseButton-secondaryFormSubmit"] {
        margin-top: 25px;
        margin-bottom: 5px;
        width: 25%;
    }

    img {
        width: 50%;
        margin: auto;
    }

    .st-emotion-cache-1y4p8pa {
        padding: 3rem 1rem 3rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

logo = st.image("asset/PCU.png")

tab1, tab2 = st.tabs(["Login", "Sign-Up"])

with tab1:
    login_form = st.form("login")
    with login_form:
        username = st.text_input("Username: ")
        password = st.text_input("Password: ", type="password")
    
        # Every form must have a submit button.
        submitted = st.form_submit_button("Login")
        if submitted:
            if username == "" or password == "":
                st.warning("Fill all the form's field")
            else:
                user_data = conn.find_user({"username": username})

                if user_data:
                    user_pass = conn.find_user({"username": username})["password"]
                    if validate_pass(password, user_pass):
                        cookies["user"] = json.dumps({
                            "_id": str(user_data["_id"]),
                            "username": user_data["username"],
                            "role": user_data["role"]
                        })
                        st.session_state.user = json.loads(cookies["user"])
                        st.switch_page("app.py")
                    else:
                        st.error("Password is incorrect, try again!")
                else:
                    st.error("Username might be incorrect, try again!")

with tab2:
    signup_form = st.form("sign-up")
    with signup_form:
        new_email = st.text_input("Email Address: ")
        new_username = st.text_input("Username: ")
        col1, col2 = st.columns(2)
        with col1:
            new_password = st.text_input("New Password: ", type="password")
        with col2:
            new_match_password = st.text_input("Re-type New Password: ", type="password")
        checkbox = st.checkbox("With this, you're confirming that the data you use to create the account is valid")

        # Every form must have a submit button.
        submitted = st.form_submit_button("Sign Up")
        if submitted:
            # Remove trailing spaces
            input = {"new_email": new_email.strip(),
                     "new_username": new_username.strip(),
                     "new_password": new_password.strip(),
                     "new_match_password": new_match_password.strip()}

            if input["new_email"] == "" or input["new_username"] == "" or input["new_password"] == "" or input["new_match_password"] == "" or not checkbox:
                st.warning("Fill all the form's field, including the checkbox")
            else:
                if input["new_password"] != input["new_match_password"]:
                    st.error("Password don't match each other, check your input!")
                elif conn.find_user({"email": input["new_email"]}) or conn.find_user({"username": input["new_username"]}):
                    st.error("There's already an account with this username or email!")
                else:
                    if not validate_email(input["new_email"]):
                        st.warning("Email input is not a valid!")
                    elif " " in input["new_password"] or " " in input["new_username"]:
                        st.warning("Whitespace is not allowed!")
                    else:
                        new_password = hash_pass(input["new_password"])
                        conn.insert_user(input["new_email"], input["new_username"], new_password)
                        st.success("Successfully created the account!")