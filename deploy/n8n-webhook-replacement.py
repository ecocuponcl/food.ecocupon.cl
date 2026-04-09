#!/usr/bin/env python3
"""
SmarterBOT n8n Webhook Replacement
══════════════════════════════════════
Replaces n8n webhook functionality while n8n workflows are being fixed.
Handles:
- POST /webhook/ecocupon → Lead ingestion
- POST /webhook/ecocupon-reward → Reward processing

Deploy: Add to lead-webhook.py or run as standalone on :9012
"""

import os
import json
import httpx
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SmarterBOT n8n Webhook Replacement", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════
BASE = Path("/opt/smarterbot")
LEADS = BASE / "agent/leads.json"
TG_BOT = os.getenv("TELEGRAM_BOT_TOKEN", "7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6683244662")

# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════
def load_leads():
    try:
        with open(LEADS) as f:
            data = json.load(f)
        if isinstance(data, list):
            return {"leads": data, "total": len(data)}
        return data
    except:
        return {"leads": [], "total": 0}

def save_leads(data):
    with open(LEADS, "w") as f:
        json.dump(data, f, indent=2, default=str)

async def send_telegram(msg):
    if not TG_BOT or not TG_CHAT:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(f"https://api.telegram.org/bot{TG_BOT}/sendMessage",
                json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"})
        return True
    except:
        return False

def score_lead(nombre, email, telefono, mensaje, producto):
    """Simple lead scoring."""
    score = 0
    
    # Product interest
    producto_upper = producto.upper() if producto else ""
    if "CLAWBOT" in producto_upper: score += 30
    elif "KIOSK" in producto_upper: score += 25
    elif "HOSTING" in producto_upper: score += 10
    else: score += 5
    
    # Message length (interest indicator)
    if mensaje:
        msg_len = len(mensaje)
        if msg_len > 100: score += 25
        elif msg_len > 50: score += 20
        elif msg_len > 20: score += 10
    
    # Phone valid
    if telefono and len(telefono) >= 8: score += 10
    
    # Email valid
    if email and "@" in email: score += 5
    
    # Keywords
    msg_lower = mensaje.lower() if mensaje else ""
    if any(kw in msg_lower for kw in ["precio", "costo", "cuanto", "demo", "implementar", "necesito"]):
        score += 15
    elif any(kw in msg_lower for kw in ["info", "información", "saber", "quiero"]):
        score += 10
    
    return min(score, 100)

# ═══════════════════════════════════════════════════════════
# WEBHOOK ENDPOINTS
# ═══════════════════════════════════════════════════════════
@app.post("/webhook/ecocupon")
@app.post("/webhook/ecocupon-reward")
async def ecocupon_webhook(request: Request):
    """Handle incoming lead from any source."""
    try:
        data = await request.json()
    except:
        return {"status": "error", "message": "Invalid JSON"}
    
    nombre = data.get("nombre", data.get("name", "Unknown"))
    email = data.get("email", "")
    telefono = data.get("telefono", data.get("phone", ""))
    mensaje = data.get("mensaje", data.get("message", ""))
    producto = data.get("product", "General")
    source = data.get("source", "webhook")
    
    # Score the lead
    score = score_lead(nombre, email, telefono, mensaje, producto)
    
    # Add to leads
    data_leads = load_leads()
    leads = data_leads.get("leads", [])
    
    # Check for duplicate
    if email and any(l.get("email") == email for l in leads):
        return {"status": "duplicate", "message": "Lead already exists"}
    
    lead_id = int(datetime.now(timezone.utc).timestamp())
    lead = {
        "id": lead_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "name": nombre,
        "email": email,
        "phone": telefono,
        "product": producto,
        "message": mensaje,
        "source": source,
        "revenue_score": score,
        "status": "hot" if score >= 70 else "warm" if score >= 40 else "cold",
        "revenue_action": "aggressive_close" if score >= 70 else "nurture" if score >= 40 else "mark_lost"
    }
    
    leads.insert(0, lead)
    data_leads["leads"] = leads
    data_leads["total"] = len(leads)
    save_leads(data_leads)
    
    # Send Telegram alert for HOT leads
    if score >= 70:
        import asyncio
        msg = (
            f"🔥 <b>NUEVO LEAD HOT!</b>\n\n"
            f"👤 {nombre}\n"
            f"📦 {producto}\n"
            f"📊 Score: {score}/100\n"
            f"📧 {email}\n"
            f"📱 {telefono}\n"
            f"💬 {mensaje[:100]}"
        )
        asyncio.get_event_loop().run_until_complete(send_telegram(msg))
    
    return {
        "status": "ok",
        "lead_id": lead_id,
        "score": score,
        "message": "Lead processed successfully"
    }

@app.get("/health")
async def health():
    return {"status": "ok", "service": "n8n-webhook-replacement"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9012, log_level="info")
