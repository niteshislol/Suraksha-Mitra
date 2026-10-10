from src.agent import agent
from src.session_manager import session_manager
import json

def test_chat():
    print("========================================")
    print("🤖 Suraksha Mitra (Ollama Conversational Agent)")
    print("========================================")
    print("Type 'exit' to quit, 'clear' to reset your session.")
    
    # We simulate a single WhatsApp user
    test_phone = "1234567890"
    
    while True:
        # Show current internal state
        session = session_manager.get_or_create_session(test_phone)
        print(f"\n[INTERNAL STATE]: {json.dumps(session.state, indent=2)}")
        
        user_message = input("\nYou: ")
        
        if user_message.lower() in ['exit', 'quit']:
            break
        elif user_message.lower() == 'clear':
            session_manager.clear_session(test_phone)
            print("[Session Cleared]")
            continue
            
        if not user_message.strip():
            continue
            
        print("\nSuraksha Mitra is typing...")
        response = agent.process_message(test_phone, user_message)
        
        print("\n🤖 Suraksha Mitra:")
        print(response)

if __name__ == "__main__":
    test_chat()
