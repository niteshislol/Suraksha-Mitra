# Twilio SMS Webhook & ngrok Integration Guide
This guide explains how to connect your local ScamShield server to a live Twilio phone number to automatically analyze incoming SMS messages and reply to them in real time.
---
## Step 1: Create a Twilio Account & Get a Number
1. **Sign Up**: Create a free trial account at [Twilio](https://www.twilio.com/try-twilio).
2. **Claim a Number**: In the Twilio Console, click **Get a trial phone number** to provision your Twilio number (e.g., `+1 234 567 8901`).
3. **Locate Credentials**: Find your **Account SID** and **Auth Token** on your console home page. You will need these to enable webhook signature validation.
---
## Step 2: Install and Run ngrok
Because your local FastAPI server runs on `http://127.0.0.1:8000`, Twilio cannot send requests to it directly. You must create a secure public tunnel to expose port 8000.
1. **Download ngrok**: Download and authenticate ngrok from [ngrok.com](https://ngrok.com/).
2. **Start the Tunnel**: Open a terminal and run the following command:
   ```bash
   ngrok http 8000
   ```
3. **Copy HTTPS URL**: ngrok will display a status screen. Copy the public **HTTPS Forwarding URL** (e.g., `https://a1b2-34-56-78.ngrok-free.app`).
---
## Step 3: Configure the Twilio Messaging Webhook
1. **Navigate to Numbers**: In the Twilio Console, go to **Phone Numbers** > **Manage** > **Active Numbers**.
2. **Select Your Number**: Click on the Twilio number you claimed in Step 1.
3. **Configure Webhook**:
   - Scroll down to the **Messaging** section.
   - Under **A MESSAGE COMES IN**, select **Webhook** in the dropdown.
   - Paste your ngrok HTTPS URL followed by the endpoint: `/api/sms-webhook` (e.g., `https://a1b2-34-56-78.ngrok-free.app/api/sms-webhook`).
   - Ensure the HTTP method next to the input is set to **HTTP POST**.
4. **Save**: Click **Save configuration** at the bottom of the page.
---
## Step 4: Webhook Signature Security Validation (Optional)
By default, ScamShield skips Twilio signature validation (`SKIP_TWILIO_VALIDATION=true` in `.env`) so you can test locally using curl/test scripts. For production, enable signature checking to verify that incoming requests originate from Twilio:
1. Open your project `.env` file.
2. Set your Twilio Auth Token:
   ```env
   TWILIO_AUTH_TOKEN=your_real_auth_token_here
   SKIP_TWILIO_VALIDATION=false
   ```
3. Restart your FastAPI server.
> [!WARNING]
> **Ngrok / Proxy Signature Gotcha**:
> Twilio signature validation depends on the *exact URL* Twilio requests. If Twilio requests `https://xxxx.ngrok-free.app/api/sms-webhook` but your local FastAPI server processes the request as `http://127.0.0.1:8000/...`, the signatures will mismatch and the request will be rejected with a `403 Forbidden` error.
> 
> ScamShield resolves this by automatically reading the proxy forwarding headers (`X-Forwarded-Proto` and `X-Forwarded-Host`) supplied by ngrok to reconstruct the external URL requested by Twilio. Make sure you do not strip these headers if you use a custom reverse proxy. Keep `SKIP_TWILIO_VALIDATION=true` for initial local verification.
---
## Step 5: Test the Integration
1. Start your local server:
   ```bash
   python -m src.main
   ```
2. Send an SMS text containing a suspicious template from your mobile phone to your Twilio number (e.g. *"Congratulations! You won ₹15000 cashback from SBI. Click to claim bit.ly/pay-upi"*).
3. The server logs the request as `source: sms` and you will receive an automatic TwiML reply within a few seconds.
