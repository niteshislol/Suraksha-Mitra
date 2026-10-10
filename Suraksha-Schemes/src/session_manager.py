import json
from datetime import datetime
from typing import Dict, List, Any

class UserSession:
    def __init__(self, phone_number: str):
        self.phone_number = phone_number
        # Stores the chat history as a list of {"role": "user"/"assistant", "content": "..."}
        self.history: List[Dict[str, str]] = []
        
        # The tracked state as defined in the implementation plan
        self.state: Dict[str, Any] = {
            "state": None,
            "district": None,
            "farming_status": None,
            "land_area_acres": None,
            "primary_need": None,
            "beneficiary_type": None,          # e.g., self, daughter, wife, son
            "beneficiary_gender": None,        # e.g., female, male
            "beneficiary_age_or_education": None, # e.g., student, child, adult, senior
            "irrigation": None,
            "farmer_registration": None,
            "existing_scheme_benefits": None
        }
        self.last_active = datetime.now()

    def add_message(self, role: str, content: str, max_history: int = 10):
        """Adds a message to the history, keeping only the most recent ones."""
        self.history.append({"role": role, "content": content})
        
        # Maintain a rolling window of history
        if len(self.history) > max_history:
            self.history = self.history[-max_history:]
            
        self.last_active = datetime.now()

    def update_state(self, new_state_data: Dict[str, Any]):
        """Updates the tracked state with newly discovered information from the LLM."""
        for key, value in new_state_data.items():
            # We only update known keys and ignore nulls from the LLM
            if key in self.state and value is not None:
                # If the LLM returns a string like "unknown" or "null", we might want to handle it carefully,
                # but for now we accept valid values.
                if str(value).lower() not in ["none", "null", "unknown"]:
                    self.state[key] = value
        self.last_active = datetime.now()

    def get_context(self) -> Dict[str, Any]:
        """Returns the full context needed for the LLM to make decisions."""
        return {
            "history": self.history,
            "state": self.state
        }
        
    def is_core_info_missing(self) -> bool:
        """Returns True if essential state elements are still missing."""
        # For our logic: primary_need (or a specific scheme name) is the ONLY absolute minimum to unlock a search.
        return self.state["primary_need"] is None


class SessionManager:
    """Manages all active user sessions."""
    def __init__(self):
        # In-memory store: {phone_number: UserSession}
        # Note: For production with multiple workers, this should be Redis or SQLite
        self.sessions: Dict[str, UserSession] = {}

    def get_or_create_session(self, phone_number: str) -> UserSession:
        """Retrieves an existing session or creates a fresh one."""
        if phone_number not in self.sessions:
            self.sessions[phone_number] = UserSession(phone_number)
        return self.sessions[phone_number]

    def clear_session(self, phone_number: str):
        """Wipes a session (useful when user types 'restart' or 'clear')."""
        if phone_number in self.sessions:
            del self.sessions[phone_number]

# Global singleton for use in the app
session_manager = SessionManager()
