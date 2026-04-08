#!/usr/bin/env python3
"""
lead-webhook.py — Simple webhook server for SmarterBOT Store forms
Receives form submissions → forwards to Telegram → logs to file
Runs on port 8003

Deploy: /opt/smarterbot/agent/lead-webhook.py
Run: uvicorn lead-webhook:app --port 8003 --host 127.0.0.1
"""

import os
import json
import httpx
import time
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SmarterBOT Lead Webhook")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["POST"], allow_headers=["*"])

# Config
TELEGRAM_BOT = os.getenv("TELEGRAM_BOT_TOKEN", "7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6683244662")
LEADS_FILE = Path("/opt/smarterbot/agent/leads.json")

def load_leads():
    try:
        with open(LEADS_FILE) as f:
            return json.load(f)
    except:
        return {"leads": [], "total": 0}

def save_leads(data):
    with open(LEADS_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

async def send_telegram(message: str):
    if not TELEGRAM_BOT or not TELEGRAM_CHAT:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT, "text": message, "parse_mode": "HTML"}
            )
            return resp.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

@app.post("/webhook/clawbot-cotizacion")
@app.post("/webhook/store-contacto")
async def receive_lead(request: Request):
    try:
        data = await request.json()
    except:
        return {"status": "error", "message": "Invalid JSON"}

    lead = {
        "id": int(time.time()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": str(request.url.path),
        "name": data.get("nombre") or data.get("name", ""),
        "email": data.get("email", ""),
        "phone": data.get("telefono") or data.get("phone", ""),
        "product": data.get("product") or data.get("service") or ("CLAWBOT" if "clawbot" in str(request.url.path) else "General"),
        "message": data.get("mensaje") or data.get("message", ""),
        "company": data.get("empresa", ""),
        "url": data.get("source_url", ""),
    }

    # Save to file
    leads = load_leads()
    leads["leads"].insert(0, lead)
    leads["leads"] = leads["leads"][:500]  # Keep last 500
    leads["total"] += 1
    save_leads(leads)

    # Send Telegram alert
    msg = f"""🔥 <b>Nuevo Lead SmarterBOT Store</b>

📦 <b>Producto:</b> {lead['product']}
👤 <b>Nombre:</b> {lead['name']}
📧 <b>Email:</b> {lead['email']}
📱 <b>WhatsApp:</b> {lead['phone']}
💬 <b>Mensaje:</b> {lead['message'][:100]}
🔗 <b>Fuente:</b> store.ecocupon.cl
⏰ <b>Fecha:</b> {lead['timestamp'][:19]}"""

    await send_telegram(msg)

    return {
        "status": "ok",
        "lead_id": lead["id"],
        "message": "Lead received! Te contactaremos pronto."
    }

@app.get("/leads")
async def get_leads(limit: int = 50):
    leads = load_leads()
    return {"total": leads["total"], "recent": leads["leads"][:limit]}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "lead-webhook", "leads_total": load_leads()["total"]}

if __name__ == "__main__":
    import uvicorn
    print(f"🟡⚫ Lead Webhook server starting on :8003", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=8003, log_level="warning")
