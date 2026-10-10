import json
import requests
from typing import Dict, Any

from src.session_manager import session_manager
from src.rag_pipeline_ollama import IndianSchemesRAGOllama, OLLAMA_MODEL, OLLAMA_URL

class SurakshaAgent:
    def __init__(self):
        # We re-use our RAG pipeline instance for searching Qdrant
        self.rag = IndianSchemesRAGOllama()

    def extract_state(self, user_message: str, current_state: Dict[str, Any], history_text: str) -> Dict[str, Any]:
        """Step A: Uses Ollama to extract any new entities from the user's message into JSON."""
        system_prompt = (
            "You are a strict data extraction tool. You will be provided with a user's message and their current known state profile. "
            "Your job is to identify any new information provided in the user's message and return a JSON object with only the updated fields. "
            "If a field is not mentioned, do NOT include it in the JSON. "
            "CRITICAL: If the user asks about or mentions a specific scheme name (e.g., 'Ayushman', 'PM Kisan'), you MUST put that scheme name into the 'primary_need' field! "
            "Allowed keys: 'state', 'district', 'farming_status', 'land_area_acres', 'primary_need', 'beneficiary_type', 'beneficiary_gender', 'beneficiary_age_or_education', 'irrigation', 'farmer_registration', 'existing_scheme_benefits'. "
            "Output ONLY valid JSON. No markdown formatting, no explanations."
        )
        
        user_prompt = f"Current State: {json.dumps(current_state)}\nRecent History: {history_text}\nUser's Latest Message: {user_message}\n\nReturn JSON:"
        
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.0,  # Zero temperature for deterministic JSON output
                    "stream": False,
                    "format": "json"    # Force Ollama to output JSON
                },
                timeout=120
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            
            # Clean up the response in case Ollama wraps it in markdown blocks
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
                
            return json.loads(content)
        except Exception as e:
            print(f"Extraction Error: {e}")
            return {}

    def generate_followup_question(self, current_state: Dict[str, Any], user_message: str) -> str:
        """Step B1: Generates exactly ONE question to gather missing core information."""
        system_prompt = (
            "You are Suraksha Mitra, a helpful WhatsApp assistant helping Indian farmers find government schemes. "
            "The farmer has not told us what kind of assistance they need yet. "
            "Your ONLY goal right now is to ask them exactly ONE friendly follow-up question to find out their 'primary_need' (e.g., loan, seeds, education, or a specific scheme). "
            "DO NOT ask about their state, district, farming status, or land size. Keep it extremely short, friendly, and in the user's language. "
            "DO NOT recommend schemes yet. Ask ONLY ONE question."
        )
        
        user_prompt = f"Current State: {json.dumps(current_state)}\nUser Message: {user_message}\n\nAsk ONE follow-up question:"
        
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,
                "stream": False
            },
            timeout=120
        )
        return response.json()["choices"][0]["message"]["content"].strip()

    def generate_search_query(self, current_state: Dict[str, Any], user_message: str) -> str:
        """Step B2a: Generates an optimized, pure English search query for the vector database."""
        system_prompt = (
            "You are an expert search query generator for a Vector Database. "
            "You will be given the user's latest message and their current profile state in JSON. "
            "Your task is to translate their intent into a highly optimized, dense, and purely ENGLISH search query. "
            "IMPORTANT RULES:\n"
            "1. ALWAYS append 'Central Government of India' along with their specific state to the query, to ensure we pull national schemes as well.\n"
            "2. Include demographic keywords explicitly (e.g., if beneficiary is daughter, include 'girl child', 'female', 'student', 'daughter').\n"
            "3. Output ONLY the generated search query string, nothing else. No quotes, no explanations."
        )
        
        user_prompt = f"Profile State: {json.dumps(current_state)}\nUser Message: {user_message}\n\nSearch Query:"
        
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.1,
                    "stream": False
                },
                timeout=120
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"Query Generation Error: {e}")
            return f"{current_state.get('primary_need', user_message)} schemes in {current_state.get('state', 'India')} for {current_state.get('beneficiary_type', 'farmers')}"

    def generate_final_recommendation(self, user_message: str, state: Dict[str, Any], search_query: str) -> str:
        """Step B2b: Searches Qdrant and generates the highly formatted final scheme recommendations."""
        
        print(f"[Agent] Optimized Search Query: '{search_query}'")
        results = self.rag.retrieve_context(search_query, limit=5)
        
        if not results:
             return "I could not find any specific schemes matching your profile at the moment."
             
        context_texts = []
        for i, hit in enumerate(results):
            text = hit.payload.get('text', '')
            context_texts.append(f"--- Document {i+1} ---\n{text}")
        full_context = "\n\n".join(context_texts)
        
        system_prompt = (
            "You are Suraksha Mitra, a helpful WhatsApp assistant. "
            "Evaluate the user's message against the retrieved official scheme documents.\n\n"
            "RULE 1: IF THE USER IS ASKING FOR A GENERAL SEARCH (e.g., 'tell me about schemes', 'need a loan'):\n"
            "Keep your response VERY SHORT. List ONLY the top 2-3 most relevant schemes.\n"
            "Format EXACTLY like this:\n"
            "*1. [Scheme Name]*\n"
            "💰 लाभ (Benefit): [Short sentence]\n"
            "🎯 उपयुक्तता (Why it fits): [Short sentence]\n\n"
            "PROGRESSIVE PROFILING RULE: After listing the schemes, if any scheme requires a specific condition we don't know (like their state, or BPL card), ask ONE friendly question about it. Otherwise, ask if they want more details.\n\n"
            "RULE 2: IF THE USER IS ASKING FOR FULL DETAILS ABOUT A SPECIFIC SCHEME (e.g., 'tell me more about ayushman', 'how to apply'):\n"
            "Provide the full, detailed information for that specific scheme ONLY. Do not use the short format. "
            "Use these headers:\n"
            "*About the Scheme:*\n[Brief description]\n\n"
            "*🎯 Eligibility:*\n[Full criteria]\n\n"
            "*💰 Key Benefits:*\n[Full benefits]\n\n"
            "*📝 How to Apply & Documents:*\n[Steps and required documents]\n"
        )
        
        user_prompt = f"Farmer Profile: {json.dumps(state)}\n\nOfficial Documents:\n{full_context}\n\nUser Message: {user_message}"
        
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2,
                "stream": False
            },
            timeout=180
        )
        return response.json()["choices"][0]["message"]["content"].strip()

    def process_message(self, phone_number: str, user_message: str, is_audio: bool = False) -> str:
        """The main entry point for an incoming WhatsApp message."""
        # 1. Get or create session
        session = session_manager.get_or_create_session(phone_number)
        
        # Convert recent history to text for context
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in session.history[-3:]])
        
        # 2. Step A - Extract new state
        print(f"\n[Agent] Extracting state for {phone_number}...")
        extracted_data = self.extract_state(user_message, session.state, history_text)
        if extracted_data:
            print(f"[Agent] Found new data: {extracted_data}")
            session.update_state(extracted_data)
            
        # 3. Step B - Decision Engine
        if not is_audio and session.is_core_info_missing():
            print("[Agent] Core info missing. Generating follow-up question...")
            bot_response = self.generate_followup_question(session.state, user_message)
        else:
            print("[Agent] Core info present (or audio forced)! Generating optimized English search query...")
            search_query = self.generate_search_query(session.state, user_message)
            print("[Agent] Searching Qdrant and generating recommendations...")
            bot_response = self.generate_final_recommendation(user_message, session.state, search_query)
            
        # 4. Save to history
        session.add_message("user", user_message)
        session.add_message("assistant", bot_response)
        
        return bot_response

# Global instance
agent = SurakshaAgent()
