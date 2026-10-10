import os
import json
import logging
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse, JSONResponse
import httpx
from dotenv import load_dotenv

# Load env variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Config
# Ensure this token is the SAME across your Gateway, ScamShield, and Suraksha apps!
VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "Suraksha-Mitra")
ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
GRAPH_API_URL = "https://graph.facebook.com/v21.0"

app = FastAPI(title="WhatsApp AI Gateway")

# In-memory session tracking: phone_number -> app_choice ('A' or 'B')
# A = Scheme Navigator (Port 8001, /webhook)
# B = Scam Shield (Port 8000, /api/whatsapp-webhook)
active_sessions = {}

async def send_whatsapp_reply(to: str, message: str):
    """Sends a text message via WhatsApp Graph API"""
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        logger.error("Missing ACCESS_TOKEN or PHONE_NUMBER_ID in Gateway.")
        return

    url = f"{GRAPH_API_URL}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": message, "preview_url": False}
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.error(f"Gateway failed to send message: {resp.text}")
        except Exception as e:
            logger.error(f"Gateway error sending message: {e}")

async def forward_webhook(payload_bytes: bytes, headers: dict, target_url: str):
    """Forwards the raw Meta webhook to the specific downstream server."""
    forward_headers = {
        "Content-Type": "application/json"
    }
    # Pass along the HMAC signature so the downstream apps don't reject it
    # Note: Meta sends lower-case headers to FastAPI
    if "x-hub-signature-256" in headers:
        forward_headers["X-Hub-Signature-256"] = headers["x-hub-signature-256"]
        
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            logger.info(f"Forwarding to {target_url}...")
            # CRITICAL: We must send the exact raw bytes to preserve the HMAC signature
            resp = await client.post(target_url, content=payload_bytes, headers=forward_headers)
            logger.info(f"Downstream response: {resp.status_code}")
        except Exception as e:
            logger.error(f"Failed to forward to {target_url}: {e}")

@app.get("/webhook")
async def verify_webhook(request: Request):
    """Handles Meta's initial Webhook Verification"""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Gateway Webhook verified successfully ✅")
        return PlainTextResponse(content=challenge, status_code=200)

    raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receives WhatsApp messages, checks session, and routes accordingly."""
    payload_bytes = await request.body()
    try:
        data = json.loads(payload_bytes)
    except:
        return JSONResponse({"status": "ok"}, status_code=200)
        
    # Standard WhatsApp parsing
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "messages":
                continue
                
            value = change.get("value", {})
            messages = value.get("messages", [])
            
            for msg in messages:
                from_num = msg.get("from")
                msg_type = msg.get("type")
                
                # Check for "stop" or "menu" text commands
                user_text = ""
                if msg_type == "text":
                    user_text = msg.get("text", {}).get("body", "").strip().lower()
                elif msg_type == "interactive":
                    interactive = msg.get("interactive", {})
                    user_text = (interactive.get("button_reply", {}).get("title") or "").strip().lower()
                    
                # 1. Reset Session Command
                if user_text in ["stop", "menu", "exit", "hi", "hello"]:
                    active_sessions.pop(from_num, None)
                    menu_msg = (
                        "🤖 *Welcome to the Central AI Gateway!*\n\n"
                        "Which assistant do you want to talk to?\n"
                        "Reply *A* for *Scheme Navigator*\n"
                        "Reply *B* for *Scam Shield*\n\n"
                        "_(You can type 'stop' anytime to return to this menu)_"
                    )
                    background_tasks.add_task(send_whatsapp_reply, from_num, menu_msg)
                    return JSONResponse({"status": "ok"}, status_code=200)

                # 2. Check if user has an active session
                current_session = active_sessions.get(from_num)
                
                if not current_session:
                    # User needs to select an app
                    if user_text == "a":
                        active_sessions[from_num] = "A"
                        background_tasks.add_task(send_whatsapp_reply, from_num, "✅ Connected to *Scheme Navigator*!\nAsk me any question about government schemes.")
                    elif user_text == "b":
                        active_sessions[from_num] = "B"
                        background_tasks.add_task(send_whatsapp_reply, from_num, "🛡️ Connected to *Scam Shield AI*!\nForward me a suspicious message or audio to analyze.")
                    else:
                        # Unknown input while no session
                        menu_msg = (
                            "Please select an assistant first:\n"
                            "Reply *A* for Scheme Navigator\n"
                            "Reply *B* for Scam Shield"
                        )
                        background_tasks.add_task(send_whatsapp_reply, from_num, menu_msg)
                        
                    return JSONResponse({"status": "ok"}, status_code=200)

                # 3. User HAS a session, so forward the exact payload to the correct app!
                target_url = None
                if current_session == "A":
                    target_url = "http://localhost:8001/webhook"
                elif current_session == "B":
                    # Based on your ngrok logs, ScamShield expects /api/whatsapp-webhook
                    target_url = "http://localhost:8000/api/whatsapp-webhook"
                    
                if target_url:
                    headers = dict(request.headers)
                    # Pass payload_bytes directly to preserve the HMAC signature!
                    background_tasks.add_task(forward_webhook, payload_bytes, headers, target_url)

    # Always return 200 OK immediately so Meta doesn't retry
    return JSONResponse({"status": "ok"}, status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)
