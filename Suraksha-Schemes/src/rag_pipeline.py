import os
import argparse
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from groq import Groq

print("Loading RAG Pipeline...")

# Constants
# Best multilingual embedding model - supports 109 languages incl. Hindi, Tamil, Telugu, Bengali etc.
EMBEDDING_MODEL = "sentence-transformers/LaBSE"
EMBEDDING_DIM = 768  # LaBSE produces 768-dimensional vectors

# Best Groq model for multilingual RAG as of 2025/26
# Updated to a currently available model
GROQ_MODEL = "qwen/qwen3.8-27b"

# Load environment variables from .env
load_dotenv()

class IndianSchemesRAG:
    def __init__(self, collection_name="indian_schemes"):
        print(f"Loading Embedding Model: {EMBEDDING_MODEL}")
        # LaBSE: Language-agnostic BERT Sentence Embedding
        # 109 languages, excellent for Hindi, Tamil, Telugu, Kannada, Bengali, etc.
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        self.collection_name = collection_name
        
        # Connect to Qdrant
        qdrant_url = os.environ.get("QDRANT_CLUSTER_URL")
        qdrant_key = os.environ.get("QDRANT_API_KEY")
        
        if qdrant_url and qdrant_key:
            print(f"Connecting to Qdrant Cloud at {qdrant_url}...")
            self.qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=60.0)
        else:
            db_path = "data/qdrant_db"
            print(f"Connecting to local Qdrant at {db_path}...")
            self.qdrant_client = QdrantClient(path=db_path, timeout=60.0)
            
        # Initialize Groq Client
        groq_api_key = os.environ.get("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set in .env file!")
            
        print("Initializing Groq Client...")
        self.groq_client = Groq(api_key=groq_api_key)
        
    def retrieve_context(self, query: str, limit: int = 5):
        """Generates an embedding for the query and retrieves the most relevant chunks from Qdrant."""
        print(f"\n[Retrieval] Searching for: '{query}'")
        query_vector = self.embedding_model.encode(query).tolist()
        
        search_result = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit
        ).points
        
        return search_result
        
    def generate_answer(self, query: str, search_results, model="qwen/qwen3.8-27b"):
        """Passes the retrieved contexts and user query to Groq LLM to generate an answer."""
        if not search_results:
            return "I could not find any relevant government schemes for your query in the database."
            
        # Compile context string
        context_texts = []
        for i, hit in enumerate(search_results):
            payload = hit.payload
            text = payload.get('text', '')
            score = round(hit.score, 4)
            # Add context with some basic formatting
            context_texts.append(f"--- Context {i+1} (Relevance Score: {score}) ---\n{text}")
            
        full_context = "\n\n".join(context_texts)
        
        system_prompt = (
            "You are Suraksha, an empathetic and highly knowledgeable AI assistant specializing in Indian Government Schemes. "
            "Your purpose is to help citizens discover, understand, and apply for government benefits, grants, and subsidies.\n\n"
            
            "=== CORE RULES ===\n"
            "1. NO HALLUCINATIONS: You must ONLY use the information provided in the Context below. If the Context does not contain the answer, you must say: 'I apologize, but I do not have the specific information regarding that. Please visit the official portal at myscheme.gov.in for accurate details.'\n"
            "2. MULTILINGUAL SUPPORT: You must respond in the exact same language the user uses (e.g., if asked in Hindi, reply in Hindi; if asked in Tamil, reply in Tamil).\n"
            "3. ACCURACY OVER COMPLETENESS: Never guess eligibility criteria, deadlines, or benefit amounts. If a specific number isn't in the context, do not state it.\n\n"
            
            "=== WHATSAPP FORMATTING GUIDELINES ===\n"
            "Format your responses to be highly readable on a mobile device:\n"
            "- Use asterisks for bold text (e.g., *Eligibility*)\n"
            "- Use underscores for italics (e.g., _Note: ..._)\n"
            "- Use bullet points (-) for lists\n"
            "- Keep paragraphs short (1-3 sentences max)\n"
            "- Use relevant emojis sparingly to make the text friendly but professional (e.g., 📝, 💰, 🏢)\n\n"
            
            "=== RESPONSE STRUCTURE ===\n"
            "When explaining a specific scheme, always try to structure your response using these exact headers (if the information exists in the context):\n"
            "*About the Scheme:*\n[Brief summary]\n\n"
            "*🎯 Eligibility:*\n[Bullet points of who can apply]\n\n"
            "*💰 Key Benefits:*\n[Bullet points of financial or material benefits]\n\n"
            "*📝 How to Apply & Documents:*\n[Application steps and required documents]"
        )
        
        user_prompt = f"Context:\n{full_context}\n\nQuestion: {query}"
        
        print(f"[Generation] Sending prompt to Groq (Model: {model})...")
        completion = self.groq_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,   # Low temperature for factual, grounded responses
            max_tokens=2048,   # Allow longer answers for scheme details
            top_p=0.9,
            stream=False,
        )
        
        return completion.choices[0].message.content, full_context

def main():
    parser = argparse.ArgumentParser(description="Query the Indian Schemes RAG Pipeline")
    parser.add_argument("--query", type=str, help="The question you want to ask", required=False)
    args = parser.parse_args()
    
    try:
        rag = IndianSchemesRAG()
    except Exception as e:
        print(f"Failed to initialize RAG Pipeline: {e}")
        print("Please ensure your .env file contains QDRANT_CLUSTER_URL, QDRANT_API_KEY, and GROQ_API_KEY.")
        return
        
    print(f"\n✅ RAG Pipeline Ready!")
    print(f"   Embedding: {EMBEDDING_MODEL} ({EMBEDDING_DIM}-dim, 109 languages)")
    print(f"   LLM:       {GROQ_MODEL} via Groq")
        
    if args.query:
        # One-off query mode
        results = rag.retrieve_context(args.query, limit=5)
        answer, context = rag.generate_answer(args.query, results, model=GROQ_MODEL)
        print("\n================ ANSWER ================\n")
        print(answer)
        print("\n========================================\n")
    else:
        # Interactive shell mode
        print("\n--- Indian Government Schemes RAG Assistant ---")
        print("Type 'exit' or 'quit' to stop.")
        while True:
            query = input("\nAsk a question: ")
            if query.lower() in ['exit', 'quit']:
                break
            if not query.strip():
                continue
                
            results = rag.retrieve_context(query, limit=5)
            answer, context = rag.generate_answer(query, results, model=GROQ_MODEL)
            
            print("\n================ ANSWER ================\n")
            print(answer)
            print("\n========================================\n")

if __name__ == "__main__":
    main()
