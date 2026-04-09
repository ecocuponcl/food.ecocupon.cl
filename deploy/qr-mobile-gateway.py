#!/usr/bin/env python3
"""
QR Mobile Gateway — Mobile Client Connection Point
════════════════════════════════════════════════════
Connects: Mobile Client → QR Scan → Revenue Engine → Google CRM → Trello

Endpoints:
  GET  /mobile/{lead_id}        → Mobile landing page
  POST /mobile/{lead_id}/scan   → Track QR scan
  GET  /mobile/{lead_id}/status → Check lead status
  POST /mobile/{lead_id}/pay    → Payment link (Flow.cl)
  GET  /mobile/{lead_id}/demo   → Google Calendar demo link

Deploy: /opt/smarterbot/qr-mobile-gateway.py
Port: :9010
"""

import os
import json
import time
import httpx
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="QR Mobile Gateway", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════
BASE = Path("/opt/smarterbot")
LEADS = BASE / "agent/leads.json"
REVENUE_LOG = BASE / "revenue-log.json"

FLOW_URL = os.getenv("FLOW_URL", "https://n8n.smarterbot.store/webhook")
REVENUE_URL = "http://127.0.0.1:8004"
BOLT_URL = "http://127.0.0.1:8002"

# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════
def now():
    return datetime.now(timezone.utc)

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

def find_lead(lead_id):
    data = load_leads()
    leads = data.get("leads", [])
    for l in leads:
        if str(l.get("id")) == str(lead_id) or l.get("name", "").lower() == str(lead_id).lower():
            return l
    return None

def score_lead(lead):
    """Same scoring as revenue engine."""
    score = 0
    product = lead.get("product", "").upper()
    if "CLAWBOT" in product: score += 30
    elif "KIOSK" in product: score += 25
    elif "HOSTING" in product: score += 10
    else: score += 5
    
    msg = lead.get("message", "")
    if len(msg) > 100: score += 25
    elif len(msg) > 50: score += 20
    elif len(msg) > 20: score += 10
    
    phone = lead.get("phone", "")
    if phone and len(phone) >= 8: score += 10
    
    email = lead.get("email", "")
    if "@" in email: score += 5
    
    msg_lower = msg.lower()
    if any(kw in msg_lower for kw in ["precio", "costo", "cuanto", "demo", "implementar"]):
        score += 15
    
    return min(score, 100)

# ═══════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════
@app.get("/mobile/{lead_id}", response_class=HTMLResponse)
async def mobile_landing(lead_id: str):
    """Mobile landing page for lead."""
    lead = find_lead(lead_id)
    if not lead:
        return HTMLResponse("<h1>Lead no encontrado</h1>")
    
    score = lead.get("revenue_score") or score_lead(lead)
    status = lead.get("status", "new")
    
    # Generate demo link
    demo_link = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text=Demo+SmarterBOT&dates=20260410T150000/20260410T153000&details=Demo+CLAWBOT:+Ventas+Pagos+CRM"
    
    # Generate payment link (placeholder for Flow.cl)
    pay_link = f"https://www.flow.cl/btn.html?token=zb21aa68cfd8df13c6030369d9946745810db853&amount=25000000"
    
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SmarterBOT — Tu Propuesta</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: -apple-system, sans-serif; background: #0a0a0a; color: #FFD700; min-height: 100vh; padding: 20px; }}
            .container {{ max-width: 400px; margin: 0 auto; }}
            .header {{ text-align: center; padding: 30px 0; }}
            .header h1 {{ font-size: 24px; margin-bottom: 8px; }}
            .header p {{ color: #888; font-size: 14px; }}
            .card {{ background: #1a1a1a; border-radius: 12px; padding: 20px; margin: 15px 0; border: 1px solid #333; }}
            .card h3 {{ font-size: 16px; margin-bottom: 8px; }}
            .card p {{ color: #ccc; font-size: 14px; line-height: 1.5; }}
            .score {{ font-size: 36px; font-weight: 800; text-align: center; padding: 20px; }}
            .score.high {{ color: #4CAF50; }}
            .score.medium {{ color: #FF9800; }}
            .score.low {{ color: #f44336; }}
            .btn {{ display: block; width: 100%; padding: 16px; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; text-align: center; text-decoration: none; margin: 10px 0; cursor: pointer; }}
            .btn-primary {{ background: #FFD700; color: #000; }}
            .btn-secondary {{ background: #333; color: #FFD700; border: 1px solid #FFD700; }}
            .urgency {{ background: #ff4444; color: white; padding: 12px; border-radius: 8px; text-align: center; margin: 15px 0; font-weight: 600; }}
            .footer {{ text-align: center; padding: 30px 0; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🟡⚫ SmarterBOT</h1>
                <p>Propuesta personalizada para {lead.get('name', 'Cliente')}</p>
            </div>
            
            <div class="urgency">
                ⚡ Quedan 3 cupos de despliegue este mes
            </div>
            
            <div class="card">
                <h3>📦 Producto</h3>
                <p>{lead.get('product', 'Solución SmarterBOT')}</p>
            </div>
            
            <div class="card">
                <h3>📊 Tu Score de Prioridad</h3>
                <div class="score {'high' if score >= 70 else 'medium' if score >= 40 else 'low'}">{score}/100</div>
                <p style="text-align:center; color:#888;">{'Prioridad ALTA — Respuesta en 2h' if score >= 70 else 'Prioridad MEDIA — Respuesta en 24h' if score >= 40 else 'Seguimiento automático'}</p>
            </div>
            
            <div class="card">
                <h3>💰 Inversión</h3>
                <p style="font-size:24px; font-weight:800;">25 UF</p>
                <p style="color:#888; font-size:12px;">Incluye: Kiosk + QR + Flow.cl + CRM + Soporte</p>
            </div>
            
            <a href="{demo_link}" class="btn btn-primary">📅 Agendar Demo Gratis</a>
            <a href="{pay_link}" class="btn btn-secondary">💳 Activar Ahora</a>
            
            <div class="footer">
                SmarterBOT v3 — Sistema Autónomo<br>
                {now().strftime('%d/%m/%Y %H:%M')}
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(html)

@app.post("/mobile/{lead_id}/scan")
async def track_scan(lead_id: str, request: Request):
    """Track QR scan from mobile."""
    lead = find_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Update lead
    lead["mobile_scan"] = now().isoformat()
    lead["mobile_scan_ip"] = request.client.host
    lead["status"] = "mobile_engaged"
    
    # Increase score for engagement
    current_score = lead.get("revenue_score", 0)
    lead["revenue_score"] = min(current_score + 10, 100)
    
    # Save
    data = load_leads()
    leads = data.get("leads", [])
    for i, l in enumerate(leads):
        if l.get("id") == lead.get("id"):
            leads[i] = lead
            break
    data["leads"] = leads
    data["total"] = len(leads)
    save_leads(data)
    
    # Trigger revenue action if score high
    if lead["revenue_score"] >= 70:
        # Notify via Telegram
        try:
            tg_bot = os.getenv("TELEGRAM_BOT_TOKEN", "7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc")
            tg_chat = os.getenv("TELEGRAM_CHAT_ID", "6683244662")
            async with httpx.AsyncClient(timeout=10) as c:
                await c.post(f"https://api.telegram.org/bot{tg_bot}/sendMessage",
                    json={"chat_id": tg_chat, "text": f"📱 {lead.get('name','?')} abrió propuesta móvil\\nScore: {lead['revenue_score']} → HOT\\nIP: {request.client.host}", "parse_mode": "HTML"})
        except:
            pass
    
    return {"status": "ok", "lead": lead.get("name"), "score": lead.get("revenue_score")}

@app.get("/mobile/{lead_id}/status")
async def lead_status(lead_id: str):
    """Check lead status."""
    lead = find_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {
        "name": lead.get("name"),
        "product": lead.get("product"),
        "score": lead.get("revenue_score"),
        "status": lead.get("status"),
        "llm_replied": bool(lead.get("llm_replied")),
        "mobile_scan": lead.get("mobile_scan"),
    }

@app.post("/mobile/{lead_id}/pay")
async def payment_link(lead_id: str):
    """Generate payment link."""
    lead = find_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Flow.cl payment link (placeholder - replace with real token)
    pay_url = f"https://www.flow.cl/btn.html?token=zb21aa68cfd8df13c6030369d9946745810db853&amount=25000000"
    
    lead["payment_link_sent"] = now().isoformat()
    data = load_leads()
    leads = data.get("leads", [])
    for i, l in enumerate(leads):
        if l.get("id") == lead.get("id"):
            leads[i] = lead
            break
    data["leads"] = leads
    save_leads(data)
    
    return {"status": "ok", "pay_url": pay_url, "amount": "25 UF"}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "qr-mobile-gateway", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9010, log_level="info")
