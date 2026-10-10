# 🇮🇳 Suraksha Mitra: AI-Powered Government Schemes Assistant

![Suraksha Mitra Demo](https://img.shields.io/badge/Status-Active-brightgreen) ![Tech Stack](https://img.shields.io/badge/Powered%20By-ElevenLabs%20%7C%20FastAPI%20%7C%20Qdrant-blue)

Suraksha Mitra is an intelligent, voice-first WhatsApp chatbot designed to bridge the massive information gap between Indian citizens and government welfare schemes.

---

## 🚨 The Pain Point

India has hundreds of incredible government schemes (Yojanas) designed to support farmers, students, women, and marginalized communities. However, the people who need these schemes the most are often the ones who never receive them. 

**Why?**
1. **Low Digital Literacy:** Finding schemes requires navigating complex, text-heavy government portals that are difficult for rural populations to use.
2. **Language Barriers:** Official documents are drafted in highly formal Hindi or English.
3. **The Typing Barrier:** Many users in rural India find it tedious or difficult to type out detailed, complex queries on a smartphone keyboard.

Because of these friction points, millions of eligible citizens miss out on life-changing financial aid, scholarships, and agricultural subsidies simply because they don't know how to ask for it.

---

## 💡 The Solution

**Suraksha Mitra** completely removes the friction of discovery by moving the entire experience to a platform the user already knows and trusts: **WhatsApp**.

Instead of typing, users can simply send a **Voice Note** in their natural language, such as:
> *"हमारे घर की financial condition सही नहीं है, हम BPL में आते हैं, हमारे लिए कौन सी योजना है?"* (Our financial condition is not good, we fall under BPL, what schemes are there for us?)

### 🎙️ The Power of ElevenLabs Scribe
To solve the "Typing Barrier," this project leverages the cutting-edge **ElevenLabs Scribe API** (`scribe_v1`). 
While traditional open-source transcription models hallucinate heavily when exposed to background noise or rural Indian dialects, ElevenLabs provides flawless, lightning-fast Hindi & English speech-to-text. It perfectly captures the user's intent directly from their voice note, converting spoken audio into a clean text query in milliseconds.

Once transcribed, the AI Agent takes over:
1. **Progressive Profiling:** It reads the transcription and extracts known entities (e.g., "Below Poverty Line"). If crucial info is missing, it asks a friendly follow-up question.
2. **Multilingual RAG:** It converts the intent into an optimized English search query and searches a massive embedded Vector Database of Indian Government Schemes.
3. **Personalized Delivery:** It translates the complex official scheme documents into a simple, actionable WhatsApp message, explaining exactly what the benefits are and how to apply.

---

## 🛠️ Detailed Tech Stack

### **Core Frameworks**
* **Python 3.10+**
* **FastAPI & Uvicorn:** High-performance async web framework to receive and route Meta's WhatsApp webhooks in real-time.

### **AI & Machine Learning (The Brain)**
* **ElevenLabs Scribe API:** Used exclusively for robust, noise-resilient audio transcription (Voice-to-Text). It effortlessly handles code-switching (Hindi + English) and varied audio quality from WhatsApp voice notes.
* **Groq Cloud (Llama 3):** Acts as the central "Agentic Brain." It handles entity extraction, dialogue management, query optimization, and translating the final answer back to the user seamlessly.
* **Ollama (Local / Cloud):** Fallback and local hosting for specialized LLM models.

### **Retrieval-Augmented Generation (RAG)**
* **Qdrant Cloud:** A highly scalable Vector Database used to store and instantly query thousands of official government scheme chunks.
* **Sentence-Transformers (`LaBSE`):** Language-agnostic BERT Sentence Embeddings used to vectorize scheme data, allowing semantic matching across languages.

### **Infrastructure & Integration**
* **Meta WhatsApp Cloud API:** Official WhatsApp Business API integration for sending and receiving rich messages and audio files.
* **Ngrok:** For secure localhost tunneling during development.
* **Custom AI Gateway Router:** A central `whatsapp_gateway.py` server that manages sessions and dynamically routes traffic between different AI services (e.g., Scheme Navigator vs. Scam Shield) on the same WhatsApp number.

---

## 🚀 Setup & Installation

**1. Clone and Install Dependencies**
```bash
git clone https://github.com/niteshislol/Suraksha-Mitra/Suraksha-Schemes.git
cd Suraksha-Mitra/Suraksha-Schemes
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**2. Configure Environment Variables**
Copy the example environment file and fill in your keys:
```bash
cp .env.example .env
```
Ensure you have API keys for:
* Meta WhatsApp Business (Access Token, Phone ID)
* ElevenLabs (Scribe API)
* Qdrant Cloud & Groq

**3. Run the Servers**
You can run the specific Suraksha server, or the central Gateway router:

```bash
# Start the Suraksha Schemes backend
uvicorn src.whatsapp_server:app --port 8001

# (Optional) Start the unified WhatsApp Gateway router
python whatsapp_gateway.py
```

**4. Connect Webhooks**
Run `ngrok http 8001` (or `5000` if using the Gateway) and paste the forwarding URL into your Meta Developer Dashboard under Webhook configurations.

---

## 📂 Repository Structure

* `/src/agent.py` - The central LLM orchestration logic (Entity Extraction, Follow-ups, RAG generation).
* `/src/whatsapp_server.py` - FastAPI server handling Meta Webhooks, ElevenLabs audio downloading & transcription, and message replies.
* `/src/session_manager.py` - In-memory session tracking for progressive profiling and context retention.
* `whatsapp_gateway.py` - Central router for multiplexing multiple AI bots onto a single WhatsApp number.
* `/Chhattisgarh Data/` & `/indian-government-schemes-2025/` - Curated government datasets (Sample CSVs provided as proof of training data).

---
*Built to empower rural India through accessible, voice-first AI.*
