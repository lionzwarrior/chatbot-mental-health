import streamlit as st
from utils.sidebar import build_sidebar
from utils.utils import get_cookies
from core.chatbot import Chatbot
import time
import ollama

cookies = get_cookies()

# Main Program
if "user" not in cookies or not cookies["user"]:
    st.switch_page("pages/authentication.py")
else:
    # Connect ollama to docker
    ollama_client = ollama.Client(host=st.secrets["ollama"]["url"][st.secrets["ollama"]["models"].index(cookies["chatbot"])])
    
    st.title("Configuration")
    
    # Sidebar
    build_sidebar()

    if "chatbot" not in st.session_state:
        # st.warning("Please configure your chatbot first!")
        st.session_state.chatbot = Chatbot()
    else:
        chatbot = st.session_state.chatbot
        current_settings = {"model": chatbot.llm, "embedding": chatbot.embedding_model, "vector_store": chatbot.vector_store}
        print(current_settings)
        
        models = [i for i in ollama_client.list().get("models")]
        model = st.selectbox("Model:", 
                             [current_settings["model"]] + [model.get("name") for model in models if model != current_settings["model"]], 
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
            st.session_state.chatbot = Chatbot(model, embedding, vector_store)
            st.success("Successfully configuring chatbot!!!")
            time.sleep(3)
            st.switch_page("app.py")