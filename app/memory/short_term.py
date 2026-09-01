from typing import Dict, List
import logging

logger = logging.getLogger("shopmate.short_term_memory")

class SessionMemoryManager:
    """
    Manages conversational short-term history buffer by session_id.
    """
    def __init__(self, max_history_turns: int = 10):
        self.max_history_turns = max_history_turns
        self._sessions: Dict[str, List[Dict[str, str]]] = {}

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        return self._sessions.get(session_id, [])

    def add_message(self, session_id: str, role: str, content: str):
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append({"role": role, "content": content})
        
        # Keep within max turns
        if len(self._sessions[session_id]) > self.max_history_turns * 2:
            self._sessions[session_id] = self._sessions[session_id][-self.max_history_turns * 2:]

    def clear_session(self, session_id: str):
        if session_id in self._sessions:
            del self._sessions[session_id]

# Global singleton
session_memory = SessionMemoryManager()
