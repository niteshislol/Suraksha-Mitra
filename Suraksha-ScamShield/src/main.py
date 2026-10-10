import logging
import os
import threading
import time
from typing import Dict

import io
import httpx
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
from PIL import Image
import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

# The modules imported below read the environment at import time, so .env loads first.
load_dotenv()
from src.observability import MODEL_INFO, RequestContextMiddleware, configure_logging, request_id_var

configure_logging(os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("scamshield.api")

from src.database import get_stats, init_db, save_feedback
from src.inference import ScamShieldInference

init_db()
# Validation is ON by default. Set SKIP_TWILIO_VALIDATION=true only for local
# testing without ngrok; a deployed webhook that skips validation lets anyone
# POST forged messages and read the analysis response.
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API", "")
SKIP_TWILIO_VALIDATION = os.getenv("SKIP_TWILIO_VALIDATION", "false").lower() == "true"
if SKIP_TWILIO_VALIDATION:
    log.warning("Twilio signature validation is disabled")

# CORS: the dashboard is served by this app, so third-party origins are not needed.
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000").split(",")
    if origin.strip()
]
# Simple in-process rate limit for the public analysis endpoint.
RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
_rate_state: Dict[str, list[float]] = {}
RATE_LIMIT_WINDOW = 60.0
# Sync endpoints and dependencies run in a threadpool, so the shared state needs a lock.
_rate_lock = threading.Lock()
# Longest message accepted.  Real SMS/WhatsApp scams are far shorter; the cap stops
# one request from tying up a worker with megabytes of text.
MAX_MESSAGE_CHARS = int(os.getenv("MAX_MESSAGE_CHARS", "2000"))


def rate_limit(request: Request) -> None:
    """Reject clients that exceed RATE_LIMIT_PER_MINUTE requests per window."""
    client = request.client.host if request.client else "unknown"
    now = time.time()
    with _rate_lock:
        hits = [stamp for stamp in _rate_state.get(client, []) if now - stamp < RATE_LIMIT_WINDOW]
        if len(hits) >= RATE_LIMIT:
            raise HTTPException(status_code=429, detail="Too many requests; slow down.")
        hits.append(now)
        _rate_state[client] = hits


def internal_error(what: str) -> HTTPException:
    """Log the real error with its request ID; tell the client only how to report it."""
    log.exception(what)
    return HTTPException(status_code=500, detail=f"{what}. Quote request ID {request_id_var.get()} when reporting it.")

analyzer = ScamShieldInference()
MODEL_INFO.labels(analyzer.model_name).set(1)
log.info("model loaded", extra={"model": analyzer.model_name})
app = FastAPI(
    title="ScamShield API",
    description="Regional-Language UPI/Payment Scam Detector with Tactic Explainer",
    version="2.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.add_middleware(RequestContextMiddleware)
class AnalyzeRequest(BaseModel):
    text: str = Field(..., description="Suspected scam message text", min_length=2, max_length=MAX_MESSAGE_CHARS)
class FeedbackRequest(BaseModel):
    message_id: str = Field(..., description="UUID of analyzed message")
    user_correction: str = Field(..., description="Correction value: 'scam' or 'legit'")
@app.post("/api/analyze", dependencies=[Depends(rate_limit)])
def analyze_message_endpoint(req: AnalyzeRequest):
    try:
        return analyzer.analyze(req.text)
    except Exception:
        raise internal_error("Inference failed")
@app.post("/api/sms-webhook")
async def twilio_sms_webhook(request: Request):
    """
    Receives incoming text messages from Twilio via url-encoded POST.
    Performs signature verification, runs inference, and returns TwiML reply.
    """
    form_data = await request.form()
    body = str(form_data.get("Body", "")).strip()

    if not body:
        raise HTTPException(status_code=400, detail="Missing Body parameter")
        
    if not SKIP_TWILIO_VALIDATION:
        signature = request.headers.get("x-twilio-signature")
        if not signature:
            raise HTTPException(status_code=403, detail="Missing X-Twilio-Signature header")
            
        # Twilio signs the public URL; behind a proxy (ngrok, Render) rebuild it from the forwarded headers.
        forwarded_proto = request.headers.get("x-forwarded-proto", "http")
        forwarded_host = request.headers.get("x-forwarded-host", request.url.netloc)
        url = f"{forwarded_proto}://{forwarded_host}{request.url.path}"
        
        params = {k: v for k, v in form_data.items()}
        
        validator = RequestValidator(TWILIO_AUTH_TOKEN)
        if not validator.validate(url, params, signature):
            raise HTTPException(status_code=403, detail="Invalid Twilio request signature")
            
    try:
        result = await run_in_threadpool(analyzer.analyze, body[:MAX_MESSAGE_CHARS], "sms")
        
        prob = int(result["scam_probability"] * 100)
        
        if result["label"] == "scam":
            tactic_names = [t["tactic"].replace("_", " ").title() for t in result["tactics"]]
            tactic_str = ", ".join(tactic_names[:3])
            reply_text = f"⚠️ This message looks like a SCAM ({prob}% confidence)."
            if tactic_str:
                reply_text += f" Detected: {tactic_str}."
            reply_text += " Do not click links or share OTP/PIN."
        else:
            reply_text = f"✅ This message looks safe ({prob}% scam confidence)."
            
        # 320 characters is two SMS segments.
        if len(reply_text) > 320:
            reply_text = reply_text[:317] + "..."
            
        response = MessagingResponse()
        response.message(reply_text)
        
        return Response(content=str(response), media_type="application/xml")
        
    except Exception:
        # Twilio retries on a 500; a valid TwiML apology is the better failure mode.
        log.exception("webhook analysis failed")
        response = MessagingResponse()
        response.message("⚠️ ScamShield is temporarily unable to analyze this message.")
        return Response(content=str(response), media_type="application/xml")

@app.get("/api/whatsapp-webhook")
def verify_whatsapp_webhook(request: Request):
    """Webhook verification for Meta WhatsApp API."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        log.info("WhatsApp webhook verified successfully!")
        return Response(content=challenge, status_code=200)
    raise HTTPException(status_code=403, detail="Invalid verify token")

@app.post("/api/whatsapp-webhook")
async def receive_whatsapp_message(request: Request):
    """Receives incoming messages from Meta WhatsApp API."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    if body.get("object") == "whatsapp_business_account":
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                
                if not messages:
                    continue
                    
                msg = messages[0]
                sender = msg.get("from")
                if not sender:
                    continue
                    
                msg_text = ""
                is_image = False
                is_audio = False
                
                if msg.get("type") == "text":
                    msg_text = msg.get("text", {}).get("body", "").strip()
                elif msg.get("type") in ["audio", "voice"]:
                    is_audio = True
                    audio_id = msg.get("audio", {}).get("id") or msg.get("voice", {}).get("id")
                    if audio_id:
                        try:
                            async with httpx.AsyncClient() as client:
                                url_req = f"https://graph.facebook.com/v20.0/{audio_id}"
                                headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
                                url_resp = await client.get(url_req, headers=headers)
                                if url_resp.status_code == 200:
                                    audio_url = url_resp.json().get("url")
                                    audio_resp = await client.get(audio_url, headers=headers)
                                    if audio_resp.status_code == 200:
                                        audio_bytes = audio_resp.content
                                        el_headers = {"xi-api-key": ELEVENLABS_API_KEY}
                                        el_data = {"model_id": "scribe_v1"}
                                        el_files = {"file": ("audio.ogg", audio_bytes, "audio/ogg")}
                                        el_resp = await client.post("https://api.elevenlabs.io/v1/speech-to-text", headers=el_headers, data=el_data, files=el_files)
                                        if el_resp.status_code == 200:
                                            msg_text = el_resp.json().get("text", "").strip()
                                        else:
                                            log.error(f"ElevenLabs error: {el_resp.text}")
                        except Exception:
                            log.exception("Audio Transcription failed")
                elif msg.get("type") == "image":
                    is_image = True
                    image_id = msg.get("image", {}).get("id")
                    if image_id:
                        try:
                            async with httpx.AsyncClient() as client:
                                url_req = f"https://graph.facebook.com/v20.0/{image_id}"
                                headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
                                url_resp = await client.get(url_req, headers=headers)
                                if url_resp.status_code == 200:
                                    image_url = url_resp.json().get("url")
                                    img_resp = await client.get(image_url, headers=headers)
                                    if img_resp.status_code == 200:
                                        img = Image.open(io.BytesIO(img_resp.content))
                                        try:
                                            msg_text = pytesseract.image_to_string(img, lang='eng+hin+ben+tam+tel').strip()
                                        except Exception:
                                            msg_text = pytesseract.image_to_string(img, lang='eng').strip()
                        except Exception:
                            log.exception("Image OCR failed")
                else:
                    continue
                
                if not msg_text:
                    if is_image:
                        async with httpx.AsyncClient() as client:
                            url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
                            headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}", "Content-Type": "application/json"}
                            payload = {"messaging_product": "whatsapp", "to": sender, "type": "text", "text": {"body": "🖼️ मुझे इस तस्वीर में कोई टेक्स्ट नहीं मिला। (No text found in image)."}}
                            await client.post(url, headers=headers, json=payload)
                    elif is_audio:
                        async with httpx.AsyncClient() as client:
                            url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
                            headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}", "Content-Type": "application/json"}
                            payload = {"messaging_product": "whatsapp", "to": sender, "type": "text", "text": {"body": "🎤 मुझे इस ऑडियो में कोई आवाज़ समझ नहीं आई। (Could not transcribe audio)."}}
                            await client.post(url, headers=headers, json=payload)
                    continue
                
                try:
                    result = await run_in_threadpool(analyzer.analyze, msg_text[:MAX_MESSAGE_CHARS], "whatsapp")
                    prob = int(result["scam_probability"] * 100)
                    
                    reply_text = ""
                    if is_image:
                        short_text = msg_text[:40].replace('\n', ' ') + "..." if len(msg_text) > 40 else msg_text.replace('\n', ' ')
                        reply_text += f"🖼️ तस्वीर में टेक्स्ट: '{short_text}'\n\n"
                    elif is_audio:
                        short_text = msg_text[:40].replace('\n', ' ') + "..." if len(msg_text) > 40 else msg_text.replace('\n', ' ')
                        reply_text += f"🎤 ऑडियो में सुना गया: '{short_text}'\n\n"

                    if result["label"] == "scam":
                        hindi_tactics = {
                            "urgency": "जल्दबाजी (Urgency)",
                            "authority_impersonation": "फर्जी पहचान (Impersonation)",
                            "false_reward": "झूठा इनाम (Fake Reward)",
                            "loss_aversion": "नुकसान का डर (Fear of Loss)",
                            "credential_phishing": "जानकारी चुराना (Phishing)",
                            "suspicious_link": "संदिग्ध लिंक (Suspicious Link)"
                        }
                        tactic_names = [hindi_tactics.get(t["tactic"], t["tactic"].replace("_", " ").title()) for t in result["tactics"]]
                        tactic_str = ", ".join(tactic_names[:3])
                        reply_text += f"⚠️ सावधान! यह मैसेज एक स्कैम (धोखाधड़ी) हो सकता है। (सुरक्षा स्कोर: {100 - prob}%)\n"
                        if tactic_str:
                            reply_text += f"संदिग्ध कारण: {tactic_str}\n"
                        reply_text += "कृपया किसी भी अनजान लिंक पर क्लिक न करें और अपना OTP या PIN किसी के साथ शेयर न करें।"
                    else:
                        safe_prob = 100 - prob
                        reply_text += f"✅ यह मैसेज सुरक्षित लग रहा है। (सुरक्षा स्कोर: {safe_prob}% सुरक्षित)\nफिर भी, हमेशा सतर्क रहें और किसी भी अनजान लिंक पर क्लिक करने से पहले सोचें।"
                        
                    # Send response via Meta Graph API
                    async with httpx.AsyncClient() as client:
                        url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
                        headers = {
                            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
                            "Content-Type": "application/json"
                        }
                        payload = {
                            "messaging_product": "whatsapp",
                            "to": sender,
                            "type": "text",
                            "text": {"body": reply_text}
                        }
                        resp = await client.post(url, headers=headers, json=payload)
                        if resp.status_code != 200:
                            log.error(f"Failed to send WhatsApp message: {resp.text}")
                except Exception:
                    log.exception("WhatsApp webhook analysis failed")
                    
        return {"status": "ok"}
    return {"status": "ignored"}

@app.post("/api/feedback")
def save_feedback_endpoint(req: FeedbackRequest):
    correction = req.user_correction.strip().lower()
    if correction not in ["scam", "legit"]:
        raise HTTPException(status_code=400, detail="Correction must be 'scam' or 'legit'")
    try:
        updated = save_feedback(req.message_id, correction)
    except Exception:
        raise internal_error("Could not save feedback")
    if not updated:
        raise HTTPException(status_code=404, detail="Unknown message_id")
    return {"status": "success", "message": "Feedback recorded successfully."}
@app.get("/api/health")
def health():
    """Liveness plus which model is actually serving, so a silent fallback is visible."""
    return {"status": "ok", "model": analyzer.model_name}


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/stats")
def get_stats_endpoint():
    try:
        return get_stats()
    except Exception:
        raise internal_error("Could not read statistics")
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
if __name__ == "__main__":
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
