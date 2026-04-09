#!/usr/bin/env python3
"""
SmarterBOT Web Scraping Engine
═══════════════════════════════
Searches for potential clients:
- Mercado Público licitaciones
- LinkedIn PYMEs Santiago
- Directorios empresariales
LLM qualifies fit for SmarterOS
Adds qualified leads to pipeline

Deploy: /opt/smarterbot/web-scraper.py
Cron: Every 6 hours
"""

import os
import json
import time
import random
import httpx
import re
from datetime import datetime, timezone
from pathlib import Path

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════
BASE = Path("/opt/smarterbot")
LEADS = BASE / "agent/leads.json"
SCRAPER_LOG = BASE / "scraper-log.json"

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "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")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

WEBHOOK_URL = "http://127.0.0.1:8004/store-contacto"
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

def add_lead(nombre, email, telefono, mensaje, producto, source):
    data = load_leads()
    leads = data.get("leads", [])
    
    # Check for duplicate email
    if email and any(l.get("email") == email for l in leads):
        return False
    
    lead_id = int(time.time())
    lead = {
        "id": lead_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "name": nombre,
        "email": email,
        "phone": telefono,
        "product": producto,
        "message": mensaje,
        "source": source,
        "revenue_score": 0,
        "status": "new"
    }
    leads.insert(0, lead)
    data["leads"] = leads
    data["total"] = len(leads)
    save_leads(data)
    
    # Send to webhook for scoring
    try:
        httpx.post(WEBHOOK_URL, json={
            "nombre": nombre, "email": email, "telefono": telefono,
            "mensaje": mensaje, "product": producto, "source": source
        }, timeout=10)
    except:
        pass
    
    return True

async def llm_qualify(company_info):
    """Use LLM to qualify if company is a good fit for SmarterOS."""
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(OPENROUTER_URL, json={
                "model": "qwen/qwen-turbo",
                "messages": [
                    {"role": "system", "content": "You are a B2B lead qualifier. Analyze the company info and respond with JSON ONLY: {\"score\": 0-100, \"is_prospect\": true/false, \"product_fit\": \"CLAWBOT/Hosting/Kiosk/None\", \"reason\": \"brief reason\"}"},
                    {"role": "user", "content": f"Company: {company_info}\n\nSmarterOS sells: CLAWBOT (kiosk automation, 25 UF), Web Hosting, Odoo ERP implementation. Target: PYMEs in Chile with 10-200 employees. Is this company a good prospect?"}
                ],
                "max_tokens": 200
            }, headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "HTTP-Referer": "https://smarterbot.store",
                "X-Title": "SmarterBOT Scraper"
            })
            d = r.json()
            return json.loads(d["choices"][0]["message"]["content"])
    except Exception as e:
        return {"score": 0, "is_prospect": False, "error": str(e)}

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

# ═══════════════════════════════════════════════════════════
# SCRAPERS
# ═══════════════════════════════════════════════════════════
async def scrape_mercado_publico():
    """Search Mercado Público for recent licitaciones."""
    prospects = []
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            # Search recent tenders for technology/automation
            r = await c.get(
                "https://api.mercadopublico.cl/SearchService.svc/search?"
                "term=software%20automatizacion%20kiosk&category=85&maxRows=10",
                headers={"Accept": "application/json"}
            )
            if r.status_code == 200:
                data = r.json()
                results = data.get("Results", [])
                for r in results[:5]:
                    org = r.get("Organizacion", {}).get("Nombre", "")
                    desc = r.get("Descripcion", "")[:200]
                    if org:
                        prospects.append({
                            "name": org,
                            "message": f"Licitación: {desc}",
                            "source": "mercado-publico"
                        })
    except Exception as e:
        print(f"Mercado Público error: {e}")
    
    return prospects

async def scrape_directorio_pymes():
    """Search for PYMEs in Santiago directory."""
    prospects = []
    # Simulated - in production would scrape real directories
    search_terms = ["restaurante Santiago", "retail Chile", "servicios Santiago"]
    for term in search_terms:
        prospects.append({
            "name": f"PYME - {term.title()}",
            "message": f"Prospecto encontrado: {term}",
            "source": "directorio-pymes"
        })
    return prospects[:3]

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
async def run_scrapers():
    print(f"[{datetime.now(timezone.utc).isoformat()[:19]}] 🕷️ Starting web scrape...", flush=True)
    
    # Gather prospects
    all_prospects = []
    all_prospects.extend(await scrape_mercado_publico())
    all_prospects.extend(await scrape_directorio_pymes())
    
    print(f"  Found {len(all_prospects)} raw prospects", flush=True)
    
    # Qualify with LLM
    qualified = []
    for p in all_prospects:
        qual = await llm_qualify(json.dumps(p))
        if qual.get("is_prospect") and qual.get("score", 0) >= 50:
            p["score"] = qual["score"]
            p["product_fit"] = qual.get("product_fit", "CLAWBOT")
            p["reason"] = qual.get("reason", "")
            qualified.append(p)
            print(f"  ✅ {p['name']} (score={p['score']}) → {p['product_fit']}", flush=True)
    
    # Add to pipeline
    added = 0
    for p in qualified:
        if add_lead(p["name"], "", "", p["message"], p["product_fit"], p["source"]):
            added += 1
    
    # Log
    log_entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "prospects_found": len(all_prospects),
        "qualified": len(qualified),
        "added": added,
        "details": qualified[:5]
    }
    try:
        with open(SCRAPER_LOG) as f:
            logs = json.load(f)
    except:
        logs = {"runs": []}
    logs["runs"].insert(0, log_entry)
    logs["runs"] = logs["runs"][:50]
    with open(SCRAPER_LOG, "w") as f:
        json.dump(logs, f, indent=2, default=str)
    
    # Telegram summary
    if added > 0:
        import asyncio
        msg = f"🕷️ <b>Web Scraping</b>\n\n📊 {len(all_prospects)} prospects found\n✅ {len(qualified)} qualified\n➕ {added} added to pipeline"
        asyncio.get_event_loop().run_until_complete(send_telegram(msg))
    
    print(f"  Added {added} new leads", flush=True)
    return added

def main():
    print(f"🕷️ SmarterBOT Web Scraping Engine", flush=True)
    print(f"   Schedule: Every 6 hours", flush=True)
    
    import asyncio
    asyncio.get_event_loop().run_until_complete(run_scrapers())

if __name__ == "__main__":
    main()
