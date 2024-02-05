import uuid

from typing import List

session_manager = None


def get_session_manager():
    global session_manager
    if session_manager is None:
        session_manager = sessionManager()
    return session_manager


class sessionManager():

    def __init__(self):
        self.session_map = {}

    def get_session(self, session_id):
        session = self.session_map[session_id]
        return session

    def generate_session(self) -> str:
        session_id = str(uuid.uuid4().hex)
        session = sessionData(session_id=session_id)
        self.session_map[session_id] = session
        return session_id

    def clear_session(self, session_id) -> str:
        if session_id in self.session_map:
            del self.session_map[session_id]
            return session_id
        return ""

    def list_session(self) -> List[str]:
        list = []
        if len(self.session_map) == 0:
            return list
        for key in self.session_map:
            list.append(key)
        return list

    def list_history(self, session_id) -> List:
        if len(self.session_map) == 0:
            return []
        if session_id in self.session_map:
            return self.session_map[session_id].history
        return []

    def add_question(self, session_id, question):
        if session_id not in self.session_map:
            self.session_map[session_id] = sessionData(session_id=session_id)
        session = self.session_map[session_id]
        session.history.append({"role": "user", "content": question})

    def add_answer(self, session_id, answer):
        if session_id not in self.session_map:
            self.session_map[session_id] = sessionData(session_id=session_id)
        session = self.session_map[session_id]
        chat_count = session.chat_count
        if chat_count >= 3:
            # 删除第一轮对话, 包含一个问题和一个答案
            del session.history[0:2]
        session.history.append({"role": "assistant", "content": answer})
        session.chat_count = chat_count + 1


class sessionData():
    def __init__(self, session_id):
        self.session_id = session_id
        self.history = []
        self.chat_count = 0


class chatContent():
    def __init__(self, role, content):
        self.role = role
        self.content = content
