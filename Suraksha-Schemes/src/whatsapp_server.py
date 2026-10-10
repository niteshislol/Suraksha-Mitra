"""
WhatsApp Business Cloud API + RAG Pipeline FastAPI Server
=========================================================
This server:
1. Handles Meta's webhook verification (GET /webhook)
2. Receives incoming WhatsApp messages (POST /webhook)
3. Passes user questions to the RAG pipeline
4. Replies via WhatsApp Cloud API using Groq + Qdrant

Required .env variables:
  WHATSAPP_VERIFY_TOKEN   - Any secret string you choose (set same in Meta Dashboard)
  WHATSAPP_ACCESS_TOKEN   - Permanent token from Meta App (System User token)
  WHATSAPP_PHONE_NUMBER_ID - Phone Number ID from Meta Dashboard
  WHATSAPP_APP_SECRET     - App Secret for HMAC signature verification
  GROQ_API_KEY            - Groq API key
  QDRANT_CLUSTER_URL      - Qdrant Cloud URL
  QDRANT_API_KEY          - Qdrant API key
"""

import os
import json
import hashlib
import hmac
import logging
import sys
import tempfile
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse, JSONResponse
from dotenv import load_dotenv

# Add src to path so we can import rag_pipeline
sys.path.insert(0, os.path.dirname(__file__))

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ─── Config ────────────────────────────────────────────────────────────────────
VERIFY_TOKEN        = os.environ.get("WHATSAPP_VERIFY_TOKEN", "suraksha_verify_token")
ACCESS_TOKEN        = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID     = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
APP_SECRET          = os.environ.get("WHATSAPP_APP_SECRET", "")
GRAPH_API_URL       = "https://graph.facebook.com/v21.0"

# Track already-processed message IDs to prevent duplicate replies
processed_message_ids: set[str] = set()

# Lazy-loaded RAG pipeline (loaded on first request, not at startup)
rag_pipeline = None


def get_rag_pipeline():
    """Deprecated: using agent.py instead"""
    pass


# ─── App Lifespan ──────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== Suraksha WhatsApp RAG Server Starting ===")
    logger.info(f"Webhook verify token: {VERIFY_TOKEN}")
    logger.info(f"Phone Number ID: {PHONE_NUMBER_ID or 'NOT SET ⚠️'}")
    logger.info(f"Access Token set: {'Yes ✅' if ACCESS_TOKEN else 'No ⚠️'}")
    yield
    logger.info("Server shutting down.")


app = FastAPI(
    title="Suraksha — Indian Schemes WhatsApp RAG Bot",
    description="WhatsApp webhook + Qdrant RAG pipeline powered by Groq",
    version="1.0.0",
    lifespan=lifespan
)


# ─── Helpers ───────────────────────────────────────────────────────────────────
def verify_hmac_signature(payload: bytes, signature_header: str | None) -> bool:
    """
    Verify the X-Hub-Signature-256 header sent by Meta.
    This ensures the request is genuinely from Meta, not a spoofed request.
    """
    if not APP_SECRET:
        logger.warning("APP_SECRET not set — skipping HMAC verification (not safe for production!)")
        return True  # Skip in dev if secret not configured

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(
        key=APP_SECRET.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature_header)


async def send_whatsapp_reply(to: str, message: str):
    """Send a text reply back to the user via WhatsApp Cloud API."""
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        logger.error("Cannot send reply — WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID not set!")
        return

    url = f"{GRAPH_API_URL}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    # WhatsApp messages have a 4096 char limit — split if needed
    max_length = 4000
    chunks = [message[i:i+max_length] for i in range(0, len(message), max_length)]

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, chunk in enumerate(chunks):
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {"body": chunk, "preview_url": False}
            }
            try:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    logger.info(f"Reply sent to {to} (part {i+1}/{len(chunks)}) ✅")
                else:
                    logger.error(f"Failed to send reply: {resp.status_code} — {resp.text}")
            except Exception as e:
                logger.error(f"Error sending WhatsApp reply: {e}")


async def send_typing_indicator(to: str):
    """Send a 'read' receipt so user sees the bot is processing."""
    # WhatsApp Cloud API doesn't have explicit typing indicator,
    # but marking as 'read' gives visual feedback
    pass


async def process_message(from_number: str, message_id: str, user_text: str, is_audio: bool = False):
    """
    Core RAG processing:
    1. Run semantic search on Qdrant
    2. Generate answer with Groq LLM
    3. Send reply back to user
    """
    global processed_message_ids

    # Idempotency check — ignore duplicate deliveries
    if message_id in processed_message_ids:
        logger.info(f"Skipping duplicate message {message_id}")
        return

    processed_message_ids.add(message_id)
    # Prevent unbounded growth
    if len(processed_message_ids) > 10000:
        processed_message_ids = set(list(processed_message_ids)[-5000:])

    logger.info(f"Processing message from {from_number}: '{user_text[:80]}...'")

    try:
        from src.agent import agent
        
        # Hand off the entire interaction to our intelligent multi-turn agent
        answer = agent.process_message(from_number, user_text, is_audio=is_audio)

        # Prepend a friendly header
        reply = f"🇮🇳 *Suraksha — Government Schemes Assistant*\n\n{answer}"
        await send_whatsapp_reply(from_number, reply)

    except Exception as e:
        logger.error(f"RAG pipeline error: {e}", exc_info=True)
        await send_whatsapp_reply(
            from_number,
            "⚠️ Sorry, I'm experiencing an issue right now. Please try again in a moment."
        )


async def process_audio_message(from_number: str, message_id: str, media_id: str):
    """Downloads audio from Meta, transcribes with Groq Whisper, and passes to agent."""
    global processed_message_ids
    if message_id in processed_message_ids:
        return
    processed_message_ids.add(message_id)
    
    logger.info(f"Processing audio message from {from_number}...")
    
    # 1. Get Media URL
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        url_resp = await client.get(f"{GRAPH_API_URL}/{media_id}", headers=headers)
        if url_resp.status_code != 200:
            logger.error(f"Failed to get media URL: {url_resp.text}")
            await send_whatsapp_reply(from_number, "⚠️ Failed to fetch audio.")
            return
            
        media_url = url_resp.json().get("url")
        
        # 2. Download Audio
        audio_resp = await client.get(media_url, headers=headers)
        if audio_resp.status_code != 200:
            logger.error(f"Failed to download audio: {audio_resp.text}")
            await send_whatsapp_reply(from_number, "⚠️ Failed to download audio.")
            return
            
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(audio_resp.content)
            tmp_path = tmp.name
            
    # 3. Transcribe with ElevenLabs Scribe
    logger.info("Transcribing audio with ElevenLabs Scribe...")
    elevenlabs_api_key = os.environ.get("ELEVENLABS_API")
    if not elevenlabs_api_key:
        logger.error("ELEVENLABS_API not set.")
        return
        
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(tmp_path, "rb") as f:
                files = {"file": ("audio.ogg", f, "audio/ogg")}
                data = {
                    "model_id": "scribe_v1",
                    "language_code": "hin"
                }
                headers = {"xi-api-key": elevenlabs_api_key}
                
                resp = await client.post("https://api.elevenlabs.io/v1/speech-to-text", files=files, data=data, headers=headers)
                
                if resp.status_code != 200:
                    logger.error(f"ElevenLabs Scribe failed: {resp.text}")
                    await send_whatsapp_reply(from_number, "⚠️ Sorry, I couldn't understand the voice note.")
                    return
                    
                transcribed_text = resp.json().get("text", "").strip()
                logger.info(f"Transcribed: '{transcribed_text}'")
                
        # 4. Pass transcribed text to the exact same async function used by text messages!
        if transcribed_text:
            # We append a visual mic cue so the user knows what was transcribed,
            # but we send the raw text to the exact same logic flow.
            await send_whatsapp_reply(from_number, f"🎤 _Voice Transcribed:_ \"{transcribed_text}\"")
            # We reuse the exact same process_message function! 
            # We append "_audio" to message_id to bypass the idempotency check in process_message
            await process_message(from_number, message_id + "_audio", transcribed_text, is_audio=True)
        else:
            await send_whatsapp_reply(from_number, "⚠️ The voice note was empty or unclear.")
            
    except Exception as e:
        logger.error(f"Audio processing error: {e}", exc_info=True)
        await send_whatsapp_reply(from_number, "⚠️ Error processing audio.")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ─── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"status": "ok", "service": "Suraksha WhatsApp RAG Bot", "version": "1.0.0"}


@app.get("/webhook")
async def verify_webhook(request: Request):
    """
    Meta calls this GET endpoint to verify your webhook URL.
    Steps:
      1. Go to Meta App Dashboard → WhatsApp → Configuration → Webhooks
      2. Enter your public HTTPS URL + /webhook
      3. Enter your VERIFY_TOKEN (same as WHATSAPP_VERIFY_TOKEN in .env)
      4. Meta will call this endpoint — return hub.challenge to confirm
    """
    mode      = request.query_params.get("hub.mode")
    token     = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    logger.info(f"Webhook verification attempt: mode={mode}, token_match={token == VERIFY_TOKEN}")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Webhook verified successfully ✅")
        return PlainTextResponse(content=challenge, status_code=200)

    logger.warning(f"Webhook verification FAILED — token mismatch (got: {token})")
    raise HTTPException(status_code=403, detail="Verification failed: token mismatch")


@app.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Meta POSTs all WhatsApp events here:
      - Incoming messages (text, image, voice, etc.)
      - Message status updates (sent, delivered, read)
      - Other events

    CRITICAL: Always return 200 OK immediately.
    Meta will retry delivery if it doesn't receive 200 within 20 seconds.
    All heavy processing (RAG, LLM) happens in a BackgroundTask.
    """
    payload = await request.body()

    # ── Security: Verify HMAC signature ────────────────────────────────────────
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_hmac_signature(payload, signature):
        logger.warning("Invalid HMAC signature — rejecting request")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # ── Parse payload ───────────────────────────────────────────────────────────
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # ── Only handle WhatsApp Business Account events ────────────────────────────
    if data.get("object") != "whatsapp_business_account":
        return JSONResponse({"status": "ignored", "reason": "not a whatsapp event"})

    # ── Extract messages from payload ───────────────────────────────────────────
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "messages":
                continue

            value = change.get("value", {})
            messages = value.get("messages", [])

            for msg in messages:
                msg_type   = msg.get("type")
                from_num   = msg.get("from")       # e.g. "919876543210"
                message_id = msg.get("id")         # e.g. "wamid.xxx"

                if msg_type == "text":
                    user_text = msg.get("text", {}).get("body", "").strip()
                    if user_text:
                        logger.info(f"Incoming text from {from_num}: {user_text[:60]}")
                        # 🔑 Run RAG in background — return 200 immediately
                        background_tasks.add_task(
                            process_message, from_num, message_id, user_text
                        )

                elif msg_type == "audio":
                    audio_id = msg.get("audio", {}).get("id")
                    if audio_id:
                        background_tasks.add_task(
                            process_audio_message, from_num, message_id, audio_id
                        )

                elif msg_type in ("image", "video", "document"):
                    logger.info(f"Received {msg_type} from {from_num} — not yet supported")
                    background_tasks.add_task(
                        send_whatsapp_reply, from_num,
                        "🙏 I currently only support text and voice messages. Please type or speak your question!"
                    )

                elif msg_type == "interactive":
                    # Handle button/list replies
                    interactive = msg.get("interactive", {})
                    reply_text = (
                        interactive.get("button_reply", {}).get("title")
                        or interactive.get("list_reply", {}).get("title")
                        or ""
                    )
                    if reply_text:
                        background_tasks.add_task(
                            process_message, from_num, message_id, reply_text
                        )

    # ── Always return 200 immediately ───────────────────────────────────────────
    return JSONResponse({"status": "ok"}, status_code=200)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "rag_loaded": rag_pipeline is not None,
        "phone_number_id_set": bool(PHONE_NUMBER_ID),
        "access_token_set": bool(ACCESS_TOKEN),
    }
