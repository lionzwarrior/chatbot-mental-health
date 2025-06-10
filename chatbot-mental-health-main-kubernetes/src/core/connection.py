import streamlit as st

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi


class Connection:
    def __init__(self):
        self.db = self.connect_db()
        self.user_db = self.db.users
        self.chat_session_db = self.db.chat_sessions
        self.chat_message_db = self.db.chat_messages

    @st.cache_resource(show_spinner=False)
    def connect_db(_self):
        client = MongoClient(
            st.secrets["mongo"]["connection_string"],
            server_api=ServerApi("1"))
        db = client.get_database('counsel@pcu')
        print("Successfuly connected to db!")
        return db

    def find_user(self, filter):
        return self.user_db.find_one(filter)

    def insert_user(self, email, username, password, role="user", assessment = ""):
        return self.user_db.insert_one(
            {
                "email": email,
                "username": username, 
                "password": password,
                "role": role,
                "assessment": assessment
            }
        )

    def update_user(self, filter, field):
        return self.user_db.find_one_and_update(filter, field)

    def delete_user(self, filter):
        return self.user_db.delete_one(filter)

    def retrieve_all_user(self):
        return self.user_db.find()

    def retrieve_user_chat_sessions(self,  username):
        return self.chat_session_db.find({"user": username}).sort({"creation_time":-1})
        
    def insert_chat_session(self, user, creation_time, chatbot, title):
        return self.chat_session_db.insert_one(
            {
                "user": user, 
                "creation_time": creation_time,
                "chatbot": chatbot,
                "title": title
            }
        )

    def find_chat_session(self, filter):
        return self.chat_session_db.find_one(filter)

    def update_chat_session(self, filter, field):
        return self.chat_session_db.find_one_and_update(filter, field)

    def delete_chat_session(self, filter):
        return self.chat_session_db.delete_one(filter)

    def get_chat_session_messages(self, filter):
        return self.chat_message_db.find(filter).sort({"time": 1})

    def insert_chat_message(self, chat_session_id, role, content, time):
        return self.chat_message_db.insert_one(
            {
                "chat_session_id": chat_session_id, 
                "role": role,
                "content": content,
                "time": time,
            }
        )

    def find_chat_message(self, filter):
        return self.chat_message_db.find_one(filter)