#!/usr/bin/env python3
"""
SmarterBOT Auto Revenue Engine — Secuencias de Cierre Autónomas
═════════════════════════════════════════════════════════════════
Principio: El sistema ya observa bien (Yin=100). Le falta Yang comercial.

Secuencias:
  T+0     → Respuesta inmediata (ya funciona via webhook)
  T+2min  → Urgencia + CTA demo
  T+10min → Propuesta directa + precio
  T+24h   → Mark as lost (limpieza de pipeline)

Scoring:
  CLAWBOT = +30 (producto premium)
  Kiosk   = +20
  Hosting = +10
  Mensaje largo (>50 chars) = +20 (interés real)
  Source webhook = +10
  LLM replied = +20

Action por score:
  >70 → aggressive_close (T+2, T+10)
  40-70 → nurture (T+10)
  <40 → mark_lost (T+24h)
"""

import os
import json
import time
import httpx
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════
BASE = Path("/opt/smarterbot")
LEADS = BASE / "agent/leads.json"
REVENUE_LOG = BASE / "revenue-log.json"

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "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")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TG_BOT = os.getenv("TELEGRAM_BOT_TOKEN", "7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6683244662")

CYCLE_SECONDS = 60  # Check every minute

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

def log_action(action, detail, status="ok"):
    entry = {"ts": now().isoformat(), "action": action, "detail": detail[:200], "status": status}
    try:
        with open(REVENUE_LOG) as f:
            data = json.load(f)
    except:
        data = {"actions": []}
    data.setdefault("actions", []).insert(0, entry)
    data["actions"] = data["actions"][:500]
    with open(REVENUE_LOG, "w") as f:
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
        log_action("telegram_error", str(e)[:100], "failed")
        return False

# ═══════════════════════════════════════════════════════════
# SCORING — Prioriza quién cerrar
# ═══════════════════════════════════════════════════════════
def score_lead(lead):
    """Score de 0-100 basado en señales de conversión."""
    score = 0
    signals = []
    
    # Producto (valor comercial)
    product = lead.get("product", "").upper()
    if "CLAWBOT" in product:
        score += 30; signals.append("product=CLAWBOT(+30)")
    elif "KIOSK" in product or "KIOSCO" in product:
        score += 25; signals.append("product=kiosk(+25)")
    elif "HOSTING" in product:
        score += 10; signals.append("product=hosting(+10)")
    elif "TIENDA" in product or "STORE" in product:
        score += 20; signals.append("product=store(+20)")
    else:
        score += 5; signals.append("product=other(+5)")
    
    # Mensaje (interés real = mensaje largo)
    msg = lead.get("message", "")
    if len(msg) > 100:
        score += 25; signals.append(f"msg_long({len(msg)})(+25)")
    elif len(msg) > 50:
        score += 20; signals.append(f"msg_medium({len(msg)})(+20)")
    elif len(msg) > 20:
        score += 10; signals.append(f"msg_short({len(msg)})(+10)")
    
    # Teléfono válido
    phone = lead.get("phone", "")
    if phone and len(phone) >= 8:
        score += 10; signals.append("phone_valid(+10)")
    
    # Email válido
    email = lead.get("email", "")
    if "@" in email:
        score += 5; signals.append("email_valid(+5)")
    
    # Fuente
    source = lead.get("source", "")
    if "webhook" in source:
        score += 5; signals.append("webhook_source(+5)")
    
    # LLM replied (interacción previa)
    if lead.get("llm_replied"):
        score += 5; signals.append("llm_replied(+5)")
    
    # Keywords de intención alta
    msg_lower = msg.lower()
    if any(kw in msg_lower for kw in ["precio", "costo", "cuanto", "cómo", "implementar", "demo", "agendar", "tiendas", "sucursal"]):
        score += 15; signals.append("high_intent_kw(+15)")
    elif any(kw in msg_lower for kw in ["info", "información", "saber", "necesito", "quiero"]):
        score += 10; signals.append("medium_intent_kw(+10)")
    
    return min(score, 100), signals

def get_action(score):
    """Decide acción basada en score."""
    if score >= 70:
        return "aggressive_close"
    elif score >= 40:
        return "nurture"
    else:
        return "mark_lost"

# ═══════════════════════════════════════════════════════════
# SECUENCIAS DE CIERRE
# ═══════════════════════════════════════════════════════════
async def sequence_t2_min(lead, score):
    """T+2min: Urgencia + CTA demo."""
    nombre = lead.get("name", "Cliente")
    producto = lead.get("product", "solución")
    
    msg = (
        f"🔥 <b>Nuevo lead HOT (score: {score})</b>\n\n"
        f"👤 {nombre} quiere info sobre {producto}.\n"
        f"📱 {lead.get('phone', 'N/A')}\n"
        f"💬 {lead.get('message', '')[:100]}\n\n"
        f"⚡ ACCIÓN: Enviar secuencia T+2min de cierre"
    )
    return await send_telegram(msg)

async def sequence_t10_min(lead, score):
    """T+10min: Propuesta directa."""
    nombre = lead.get("name", "Cliente")
    producto = lead.get("product", "solución")
    
    msg = (
        f"💰 <b>Secuencia T+10min — {nombre}</b>\n\n"
        f"Producto: {producto}\n"
        f"Score: {score}/100\n"
        f"Acción: Propuesta directa enviada"
    )
    return await send_telegram(msg)

def mark_lost(lead):
    """T+24h: Mark as lost si no hay respuesta."""
    lead["status"] = "lost"
    lead["lost_at"] = now().isoformat()
    lead["lost_reason"] = "no_response_24h"
    log_action("mark_lost", f"{lead.get('name', '?')} — no response 24h", "info")
    return lead

# ═══════════════════════════════════════════════════════════
# MAIN LOOP — Process leads cada minuto
# ═══════════════════════════════════════════════════════════
def process_leads():
    """Process all unprocessed leads."""
    data = load_leads()
    leads = data.get("leads", [])
    actions_taken = []
    
    for lead in leads:
        # Skip if already scored
        if lead.get("revenue_score") is not None:
            continue
        
        # Score
        score, signals = score_lead(lead)
        lead["revenue_score"] = score
        lead["revenue_signals"] = signals
        lead["revenue_at"] = now().isoformat()
        
        # Action
        action = get_action(score)
        lead["revenue_action"] = action
        actions_taken.append(f"{lead.get('name','?')}={score}→{action}")
        
        log_action("score_lead", f"{lead.get('name','?')}: {score} → {action}", "ok")
        
        # Execute sequence based on action
        if action == "aggressive_close":
            lead["sequence_t0"] = now().isoformat()
            lead["sequence_t2_due"] = (now() + timedelta(minutes=2)).isoformat()
            lead["sequence_t10_due"] = (now() + timedelta(minutes=10)).isoformat()
            lead["sequence_t24_due"] = (now() + timedelta(hours=24)).isoformat()
            lead["status"] = "hot"
        elif action == "nurture":
            lead["sequence_t0"] = now().isoformat()
            lead["sequence_t10_due"] = (now() + timedelta(minutes=10)).isoformat()
            lead["status"] = "warm"
        else:
            lead["status"] = "cold"
            lead["sequence_t24_due"] = (now() + timedelta(hours=24)).isoformat()
    
    # Check for pending sequences
    now_ts = now()
    for lead in leads:
        if lead.get("status") == "hot" and lead.get("sequence_t2_due"):
            t2 = datetime.fromisoformat(lead["sequence_t2_due"])
            if now_ts >= t2 and not lead.get("sequence_t2_sent"):
                asyncio.get_event_loop().run_until_complete(sequence_t2_min(lead, lead["revenue_score"]))
                lead["sequence_t2_sent"] = now_ts.isoformat()
                log_action("sequence_t2", f"{lead.get('name','?')} T+2min", "ok")
        
        if lead.get("sequence_t10_due") and not lead.get("sequence_t10_sent"):
            t10 = datetime.fromisoformat(lead["sequence_t10_due"])
            if now_ts >= t10:
                asyncio.get_event_loop().run_until_complete(sequence_t10_min(lead, lead.get("revenue_score", 0)))
                lead["sequence_t10_sent"] = now_ts.isoformat()
                log_action("sequence_t10", f"{lead.get('name','?')} T+10min", "ok")
        
        if lead.get("sequence_t24_due") and not lead.get("sequence_t24_sent") and not lead.get("llm_replied"):
            t24 = datetime.fromisoformat(lead["sequence_t24_due"])
            if now_ts >= t24:
                mark_lost(lead)
                lead["sequence_t24_sent"] = now_ts.isoformat()
    
    save_leads(data)
    return actions_taken

# ═══════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════
def main():
    print(f"💰 SmarterBOT Auto Revenue Engine", flush=True)
    print(f"   Scoring + Sequences (T+0, T+2, T+10, T+24h)", flush=True)
    print(f"   Cycle: {CYCLE_SECONDS}s", flush=True)
    
    while True:
        try:
            actions = process_leads()
            if actions:
                print(f"[{now().isoformat()[:19]}] Actions: {actions}", flush=True)
            else:
                print(f"[{now().isoformat()[:19]}] No new leads to process", flush=True)
        except Exception as e:
            print(f"[ERROR] {e}", flush=True)
            log_action("revenue_error", str(e), "failed")
        
        time.sleep(CYCLE_SECONDS)

if __name__ == "__main__":
    main()
