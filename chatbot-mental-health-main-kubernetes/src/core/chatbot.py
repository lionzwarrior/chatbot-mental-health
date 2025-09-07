import streamlit as st

from llama_index.llms.ollama import Ollama
from llama_index.core.llms import ChatMessage
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException
from llama_index.core import VectorStoreIndex, Settings
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.fastembed import FastEmbedEmbedding

from llama_index.core.storage.chat_store import SimpleChatStore
from llama_index.core.memory import ChatMemoryBuffer

import time
import json
from utils.utils import get_cookies
from bson import ObjectId
from core.connection import Connection
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from utils.metrics import observe_chatbot_response_time

conn = Connection()
cookies = get_cookies()
MAX_CONTEXT_TOKENS = 1126

CONTEXT_PROMPT = """You are a christian counseling chatbot for Petra Christian University, able to have normal interactions, 
                and knowledgeable in mental health issue. Context information is below.
                ---------------------\n
                {context_str}\n
                ---------------------\n
                Given the context and not prior knowledge, answer the query as concise as possible \n
                Instruction: Use the context above, to interact and help the user. If you feels that the 
                user needs further counseling or information tell them to visit Pusat Konseling dan Pengembangan Pribadi
                (PKPP) at Universitas Kristen Petra, Gedung D.111 which is located at Jl. Siwalankerto 121-131, Surabaya 
                with operational hours: Senin - Jumat, 07.30 - 15.30 WIB. Also here is the contact information of 
                Telepon/WA: +62 895-2330-5960 and Website https://pkpp.petra.ac.id/"""

if "chatbot" not in cookies or not cookies["chatbot"]:
    cookies["chatbot"] = "llama3.1:latest"

if "embedding" not in cookies or not cookies["embedding"]:
    cookies["embedding"] = "intfloat/multilingual-e5-large"

if "vector_store" not in cookies or not cookies["vector_store"]:
    cookies["vector_store"] = "Qdrant"


class Chatbot:

    def __init__(
        self,
        llm=cookies["chatbot"],
        embedding_model=cookies["embedding"],
        vector_store=cookies["vector_store"],
    ):
        # Set user
        if "user" in cookies:
            st.session_state.user = json.loads(cookies["user"])

        if conn.find_user({"_id": ObjectId(st.session_state.user["_id"])})[
            "assessment"
        ]:
            self.user_assessment = conn.find_user(
                {"_id": ObjectId(st.session_state.user["_id"])}
            )["assessment"]
        else:
            self.user_assessment = ""

        # Set setting
        self.llm = llm
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.Settings = self.set_setting()

        # Indexing
        self.client, self.index = self.load_index()

        # Chat History
        self.chat_store = ""
        self.chat_history = ""

        # Chat Engine
        self.chat_engine = self.create_chat_engine(self.index)

        print("Initialized:", self.llm, self.embedding_model, self.vector_store)

    def set_setting(self):
        Settings.llm = Ollama(
            model=self.llm,
            base_url=st.secrets["ollama"]["url"],
            request_timeout=600,
        )
        Settings.embed_model = FastEmbedEmbedding(
            model_name=self.embedding_model, cache_dir="../fastembed_cache", device="cpu"
        )
        Settings.system_prompt = f"""
            You are a religious CHRISTIAN expert system called Counsel@PCU-Bot whose role is to be a multi-lingual and experienced counselor
            extensive knowledge in the world of psychology and will only answer based on valid data.
            Your main task is to have conversations with users, listen to their stories, or
            answer questions from users about the psychology domain as naturally as possible. As a counselor, first things first
            It is important that when a user shares a story or feeling with you, you will continue the conversation by asking a few questions about 
            the user's answers until you get context of the user's mental condition in detail such as storyline, causes, consequences, current 
            treatment and otherspart of the story. In general, you will do this by asking questions
            then wait for the user's answer one by one. You will do this gradually until you really grasp the complete context for
            helping them. Even in conversation, you will empathize with them WITHOUT JUDGMENT.
            If a user makes a mistake, you must be able to gently persuade them. If you don't know
            the answer, or even after you ask further you still don't know the answer then say you 
            don't know and give your empathy to the user. Always use user-friendly language.
            Finally, the answers, solutions or suggestions you offer are prioritized in user language and based on
            a combination of biblical, spiritual, Christian and scientific elements in your knowledge.
            The most important thing is to avoid providing premature solution assumptions to the user if the user's context is not
            detailed and comprehensive enough, have a conversation as above and then provide a solution that you feel is appropriate. 
            After that don't forget when the session is over, say thank you and encourage them that they are not alone in their journey and you will always be willing to help them."""

        if self.user_assessment != "":
            Settings.system_prompt += f"""Below is the context about the user that you may use if the question is heavily related to user's personal profile and it's 
            one of the main keys for analyzing the answer:\n{self.user_assessment}"""

        return Settings

    def load_index(_self):
        with st.spinner(text="Loading index – hang tight!"):
            client = QdrantClient(url=st.secrets["qdrant"]["url"])
            vector_store = QdrantVectorStore(
                client=client, collection_name="Counsel@PCU"
            )
            index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
        return client, index

    def set_chat_history(self, messages):
        total_tokens = 0
        trimmed = []

        for msg in reversed(messages):
            tokens = int(len(msg["content"].split()) * 1.3)
            if total_tokens + tokens > MAX_CONTEXT_TOKENS:
                break
            trimmed.append(msg)
            total_tokens += tokens

        trimmed.reverse()

        self.chat_history = [
            ChatMessage(role=msg["role"], content=msg["content"]) for msg in trimmed
        ]
        self.chat_store.store = {"chat_history": self.chat_history}

    def create_chat_engine(self, index):
        self.chat_store = SimpleChatStore()
        self.memory = ChatMemoryBuffer.from_defaults(chat_store=self.chat_store)
        return index.as_chat_engine(
            chat_mode="condense_plus_context",
            chat_store_key="chat_history",
            memory=self.memory,
            llm=self.Settings.llm,
            system_prompt=Settings.system_prompt,
            context_prompt=CONTEXT_PROMPT,
            verbose=True,
        )

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(ResponseHandlingException),
        reraise=True,
    )
    def _call_chat_engine_chat_with_retries(self, prompt):
        print(f"Attempting chat_engine.chat for prompt: {prompt}")
        return self.chat_engine.chat(prompt)

    def response_generator(self, prompt):
        if "language" not in cookies or not cookies["language"]:
            cookies["language"] = "IND"
            st.session_state.language = "IND"
        else:
            st.session_state.language = cookies["language"]

        if st.session_state.language == "IND":
            language_prompt = ", jawab dalam bahasa Indonesia"
        else:
            language_prompt = ", answer in English language"
        try:
            prompt += language_prompt
        except:
            prompt = self.chat_store.get_messages("chat_history")[-1].content
            prompt += language_prompt

        start_time = time.time()
        response = self._call_chat_engine_chat_with_retries(prompt).response
        end_time = time.time()
        elapsed_time = end_time - start_time
        observe_chatbot_response_time(elapsed_time, model_name=cookies["chatbot"])
        print(f"Response Time: {elapsed_time:.4f} seconds\n")

        return response

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(ResponseHandlingException),
        reraise=True,
    )
    def _call_chat_engine_stream_chat_with_retries(self, prompt):
        """
        Internal method to encapsulate the actual Qdrant-dependent chat engine call
        with retry logic.
        """
        print(f"Attempting chat_engine.stream_chat for prompt: {prompt}")
        return self.chat_engine.stream_chat(prompt)

    def stream_response_generator(self, prompt):
        if "language" not in cookies or not cookies["language"]:
            cookies["language"] = "IND"
            st.session_state.language = "IND"
        else:
            st.session_state.language = cookies["language"]

        if st.session_state.language == "IND":
            language_prompt = ", jawab dalam bahasa Indonesia"
        else:
            language_prompt = ", answer in English language"
        try:
            prompt += language_prompt
        except TypeError:
            if isinstance(prompt, str):
                prompt += language_prompt
            else:
                try:
                    last_message_content = self.chat_store.get_messages("chat_history")[
                        -1
                    ].content
                    prompt = last_message_content + language_prompt
                except IndexError:
                    print(
                        "Warning: chat_history is empty, cannot append language prompt to last message."
                    )
                    if isinstance(prompt, str):
                        prompt += language_prompt
                    else:
                        pass

        start_time = time.time()

        try:
            response = self._call_chat_engine_stream_chat_with_retries(prompt)

            end_time = time.time()
            elapsed_time = end_time - start_time
            observe_chatbot_response_time(elapsed_time, model_name=cookies["chatbot"])
            print(f"Response Time: {elapsed_time:.4f} seconds (including retries)\n")

            for token in response.response_gen:
                yield token + ""

        except ResponseHandlingException as e:
            print(f"Failed to get response from Qdrant after multiple retries: {e}")
            yield f"Error: Failed to connect to the knowledge base. Please try again later. ({e})"
        except Exception as e:
            print(f"An unexpected error occurred in stream_response_generator: {e}")
            yield f"An unexpected error occurred: {e}"

    def get_setting(self):
        settings = {
            "llm": self.llm,
            "embedding_model": self.embedding_model,
            "vector_store": self.vector_store,
        }
        return settings
