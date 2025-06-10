from streamlit_cookies_manager import EncryptedCookieManager
import streamlit as st
import os

cookies = None

@st.cache_resource(experimental_allow_widgets=True)
def get_cookie_manager():
    secret = os.getenv("COOKIE_SECRET", "your_very_secret_key")
    # cookies = EncryptedCookieManager(password="your_very_secret_key")
    cookies = EncryptedCookieManager(password=secret)
    if not cookies.ready():
        import streamlit as st
        st.stop()
    return cookies

def get_cookies():
    global cookies
    if cookies is None:
        cookies = get_cookie_manager()
    return cookies

    