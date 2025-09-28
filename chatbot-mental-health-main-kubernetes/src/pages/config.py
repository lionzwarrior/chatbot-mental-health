import json
import os
import streamlit as st
import time
import ollama
from streamlit_cookies_manager import EncryptedCookieManager

from utils.sidebar import build_sidebar
from core.chatbot import Chatbot

secret = os.getenv("COOKIE_SECRET", "your_very_secret_key")
cookies = EncryptedCookieManager(password=secret)

if not cookies.ready():
    st.stop()

# Main Program
if "user" not in cookies or not cookies["user"]:
    st.switch_page("pages/authentication.py")
else:
    if "user" not in st.session_state:
        st.session_state.user = json.loads(cookies["user"])
    # Connect ollama to docker
    ollama_client = ollama.Client(host=st.secrets["ollama"]["url"])
    
    st.title("Configuration")
    
    # Sidebar
    build_sidebar(cookies)

    if "chatbot" not in st.session_state:
        # st.warning("Please configure your chatbot first!")
        st.session_state.chatbot = Chatbot()
    else:
        chatbot = st.session_state.chatbot
        current_settings = {"model": chatbot.llm, "embedding": chatbot.embedding_model, "vector_store": chatbot.vector_store}
        print(current_settings)
        
        models = [i for i in ollama_client.list().get("models")]
        model = st.selectbox(
                    "Model:",
                    [current_settings["model"]] + [
                        m.model for m in models if m.model != current_settings["model"]
                    ],
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
            cookies["embedding"] = embedding
            cookies["vector_store"] = vector_store
            cookies.save()
            st.session_state.chatbot = Chatbot(model, embedding, vector_store, user_id=st.session_state.user["_id"])
            st.success("Successfully configuring chatbot!!!")
            time.sleep(3)
            st.switch_page("app.py")
