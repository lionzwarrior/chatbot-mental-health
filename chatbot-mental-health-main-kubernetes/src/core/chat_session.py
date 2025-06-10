import streamlit as st
from datetime import datetime, timedelta, timezone
from core.connection import Connection


conn = Connection()
tz = timezone(timedelta(hours=7))

class ChatSession:

    def __init__(self, *args):
        if len(args) > 1:
            self._id = ""
            self.user = args[0]
            self.creation_time = datetime.now().astimezone(tz).strftime('%Y/%m/%d %H:%M:%S')
            self.chatbot = args[1].get_setting()
            self.title = self.creation_time
            self.insert_to_db()
            self.messages = []
        else:
            self._id = args[0]["_id"]
            self.user = args[0]["user"]
            self.creation_time = args[0]["creation_time"]
            self.chatbot = args[0]["chatbot"]
            self.title = args[0]["title"]
            self.messages = self.get_chat_history()

    def insert_to_db(self):
        if conn.insert_chat_session(self.user, self.creation_time, self.chatbot, self.title):
            chat_session = conn.find_chat_session(
                {"user": self.user,
                 "creation_time": self.creation_time,
                 "chatbot": self.chatbot,
                 "title": self.title
                }
            )
            self._id = chat_session["_id"]
            return True
        return False

    def get_chat_history(_self):
        filter = {"chat_session_id": _self._id}
        _self.messages = [message for message in conn.get_chat_session_messages(filter)]
        return _self.messages

    def chat(self, message):
        chat_message = ChatMessage(self._id, message["role"], message["content"])
        self.messages.append(chat_message)

    def update_title(self, title):
        self.title = title
        print(self.creation_time)
        filter = {"_id": self._id}
        return conn.update_chat_session(filter, {"$set": {"title": title}})


class ChatMessage():

    def __init__(self, chat_session_id, role, content):
        self._id = ""
        self.chat_session_id = chat_session_id
        self.role = role
        self.content = content
        self.time = datetime.now().astimezone(tz).strftime('%Y/%m/%d %H:%M:%S')
        self.insert_to_db()

    def insert_to_db(self):
        if conn.insert_chat_message(self.chat_session_id, self.role, self.content, self.time):
            chat_message = conn.find_chat_message(
                {
                    "chat_session_id": self.chat_session_id, 
                    "role": self.role,
                    "content": self.content,
                    "time": self.time}
            )
            self._id = chat_message["_id"]
            return True
        return False