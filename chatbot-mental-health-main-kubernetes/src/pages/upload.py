import os
import validators
import streamlit as st

from utils.sidebar import build_sidebar
from core.chatbot import Chatbot

from unstructured.partition.html import partition_html
from llama_index.readers.web import SimpleWebPageReader
from llama_index.readers.web import TrafilaturaWebReader
from llama_index.core import SummaryIndex
from langchain_community.document_loaders import AsyncChromiumLoader
from langchain_community.document_transformers import Html2TextTransformer

from qdrant_client import QdrantClient
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.storage.storage_context import StorageContext
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.readers.file import UnstructuredReader
from llama_index.readers.json import JSONReader


def reset_chatbot():
    if "chatbot" in st.session_state:
        chatbot = st.session_state.chatbot
        settings = chatbot.get_setting()
        st.session_state.chatbot = Chatbot(settings["llm"], settings["embedding_model"], settings["vector_store"])
        print(st.session_state.chatbot.get_setting())
    else:
        st.switch_page("app.py")


def upload_files(files, path):
    files_path = []
    for file in files:
        try:
            save_path = os.path.join(path, file.name)
            if os.path.exists(save_path):
                st.markdown("""
                <style>
                    [data-testid=stToast] {
                        background-color: #FFC152;
                    }
                </style>
                """, unsafe_allow_html=True)
                st.toast("{} already exists!".format(file.name), icon="⚠")
            else:
                with open(save_path, "wb") as f:
                    f.write(file.getvalue())
                    files_path.append(file.name)
                    indexing_data(path, file.name)
        except Exception as e:
            st.error(f"Error saving file: {e}")
            return None
    files_path = ", ".join(files_path)
    if files_path:
        print("Before")
        st.success("Successfully uploaded {}".format(files_path))
        reset_chatbot()


def validate_url(url):
    return validators.url(url)


def upload_url(url, title, path):
    valid = validate_url(url)
    if valid:
        loader = AsyncChromiumLoader([url])
        html = loader.load()
        html2text = Html2TextTransformer()
        docs = html2text.transform_documents(html)
        print(docs)
        file_name = f"{title}.txt"
        save_path = os.path.join(path, file_name)
        with open(save_path, "wb") as f:
            f.write(str.encode(docs[0].page_content))
        indexing_data(path, file_name)
    else:
        st.error("URL is not valid!")


def display_files(path):
    file_list = [file for file in os.listdir(path) if not file.startswith(".")]
    delete_button = []

    for i, file in enumerate(file_list):
        with st.container(border=True):
            col1, col2, col3 = st.columns([9, 1.5, 1])
            with col1:
                st.write(f"📄 {file}")
            with col2:
                size = os.stat(os.path.join(path, file)).st_size
                st.write(f"{round(size / (1024 * 1024), 2)} MB")
            with col3:
                delete = st.button("🗑️", key="delete"+str(i))
                delete_button.append(delete)

    if True in delete_button:
        index = delete_button.index(True)
        os.remove(os.path.join(path, file_list[index]))
        st.toast(f"Successfully deleted {file_list[index]}", icon="❌")
        del file_list[index]
        st.rerun()


def indexing_data(path, file_name):
    file_path = os.path.join(path, file_name)
    print(file_path)
    with st.spinner(text="Loading and indexing – hang tight! This should take a few minutes, don't turn off or switch pages!"):
        # Read & load document
        reader = SimpleDirectoryReader(input_files=[file_path], file_extractor={
            ".pdf":UnstructuredReader(),
            ".json":JSONReader(),
        })
        documents = reader.load_data()

        component = os.path.splitext(file_name)
        collection_name = component[0]

        # General Collection
        create_collection(documents, "Counsel@PCU")

        # Specific Index
        # create_collection(documents, collection_name)


def create_collection(documents, collection_name):
    # Create Qdrant client & store
    if not st.session_state.chatbot:
        client = QdrantClient(url=st.secrets["qdrant"]["url"])
    else:
        chatbot = st.session_state.chatbot
        client = chatbot.client
    vector_store = QdrantVectorStore(client=client, collection_name=collection_name)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
    return index


def reindex():
    # Create Qdrant client & store
    if not st.session_state.chatbot:
        client = QdrantClient(url=st.secrets["qdrant"]["url"])
    else:
        chatbot = st.session_state.chatbot
        client = chatbot.client

    # Delete collection
    client.delete_collection(collection_name="Counsel@PCU")

    # Reindexing
    path = "docs"
    file_list = [file for file in os.listdir(path) if not file.startswith(".")]
    for file in file_list:
        indexing_data(path, file)
    st.success("Successfully reset index")

# Styling
st.markdown(
    """
<style>
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
    p {
        padding: 0.45rem 0 0.45rem;
    }
    .stButton button[kind="secondary"] {
        height: 0;
        width: 100%;
    }
    .row-widget.stButton {
        display: flex;
        justify-content: center;
    }
    button[kind="secondaryFormSubmit"] {
        width: 95%;
    }
</style>
""",
    unsafe_allow_html=True,
)


# Main Program
if "user" not in st.session_state:
    st.switch_page("pages/authentication.py")
else:
    build_sidebar()
    st.session_state.chatbot = Chatbot()
    chatbot = st.session_state.chatbot

    tab1, tab2 = st.tabs(["Upload", "Management"])
    with tab1:
        st.header("Upload Files")
        with st.form("Upload", clear_on_submit=True):
            st.info("Upload documents, website URL, or both!")
            subtab1, subtab2 = st.tabs(["Documents", "Web URL"])
            with subtab1:
                files = st.file_uploader("Document:", accept_multiple_files=True)
            with subtab2:
                col1, col2 = st.columns(2)
                with col1:
                    web_url = st.text_input("Web URL:")
                with col2:
                    web_title = st.text_input("Title:")
            upload_button = st.form_submit_button("Upload")

        path = "docs"

        if upload_button:
            if not files and not web_url:
                st.warning("Input Files or URLs with Title first before uploading!")
            else:
                if files is not None:
                    upload_files(files, path)
                if web_url != "":
                    if web_title is not None:
                        upload_url(web_url, web_title, path)
                    else:
                        st.warning("Title must be included for web_url input!")
    with tab2:
        st.header("File List")
        reset_vector = st.button("🔄 Re-index")
        if reset_vector:
            reindex()
        st.warning("Changes will take effect immediately!")
        display_files(path)