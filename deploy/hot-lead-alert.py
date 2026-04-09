#!/usr/bin/env python3
"""
Telegram HOT Lead Alert — Monitors leads and alerts when score > 85
══════════════════════════════════════════════════════════════════
Deploy: /opt/smarterbot/hot-lead-alert.py
Run: systemd service every 2 minutes
"""

import os
import json
import time
import httpx
from datetime import datetime, timezone
from pathlib import Path

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════
LEADS = Path("/opt/smarterbot/agent/leads.json")
ALERT_LOG = Path("/opt/smarterbot/hot-lead-alerts.json")
HOT_THRESHOLD = 85
CHECK_INTERVAL = 120  # 2 minutes

TG_BOT = os.getenv("TELEGRAM_BOT_TOKEN", "7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6683244662")

def load_leads():
    try:
        with open(LEADS) as f:
            data = json.load(f)
        return data.get("leads", []) if isinstance(data, dict) else data
    except:
        return []

def load_alerted():
    try:
        with open(ALERT_LOG) as f:
            data = json.load(f)
        return {str(a.get("lead_id")) for a in data.get("alerted", [])}
    except:
        return set()

def save_alert(lead):
    try:
        with open(ALERT_LOG) as f:
            data = json.load(f)
    except:
        data = {"alerted": []}
    data["alerted"].append({"lead_id": lead.get("id"), "score": lead.get("revenue_score"), "ts": datetime.now(timezone.utc).isoformat()})
    data["alerted"] = data["alerted"][-100:]
    with open(ALERT_LOG, "w") as f:
        json.dump(data, f, indent=2, default=str)

async def send_telegram(msg):
    if not TG_BOT or not TG_CHAT:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(
                f"https://api.telegram.org/bot{TG_BOT}/sendMessage",
                json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"},
                timeout=10
            )
        return True
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def check_hot_leads():
    """Check for new HOT leads and alert."""
    leads = load_leads()
    alerted = load_alerted()
    new_alerts = []
    
    for lead in leads:
        score = lead.get("revenue_score", 0)
        lead_id = str(lead.get("id"))
        
        if score >= HOT_THRESHOLD and lead_id not in alerted:
            # HOT lead detected!
            nombre = lead.get("name", "Unknown")
            producto = lead.get("product", "Unknown")
            mensaje = lead.get("message", "")[:100]
            telefono = lead.get("phone", "N/A")
            email = lead.get("email", "N/A")
            
            msg = (
                f"🔥 <b>LEAD HOT DETECTADO!</b> 🔥\n\n"
                f"👤 <b>{nombre}</b>\n"
                f"📦 Producto: {producto}\n"
                f"📊 Score: {score}/100\n"
                f"📱 Tel: {telefono}\n"
                f"📧 Email: {email}\n"
                f"💬 Mensaje: {mensaje}\n\n"
                f"⚡ <b>ACCION:</b> aggressive_close\n"
                f"⏰ Enviar secuencia T+2min + T+10min\n\n"
                f"🔗 Mobile: https://qr.ecocupon.cl/mobile/{lead_id}"
            )
            
            import asyncio
            asyncio.get_event_loop().run_until_complete(send_telegram(msg))
            save_alert(lead)
            new_alerts.append(lead_id)
            print(f"[{datetime.now(timezone.utc).isoformat()[:19]}] 🔥 HOT lead: {nombre} (score={score})")
    
    return new_alerts

def main():
    print(f"🔥 HOT Lead Alert — Threshold: {HOT_THRESHOLD}", flush=True)
    print(f"   Check interval: {CHECK_INTERVAL}s", flush=True)
    
    while True:
        try:
            alerts = check_hot_leads()
            if not alerts:
                print(f"[{datetime.now(timezone.utc).isoformat()[:19]}] No new HOT leads", flush=True)
        except Exception as e:
            print(f"ERROR: {e}", flush=True)
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
