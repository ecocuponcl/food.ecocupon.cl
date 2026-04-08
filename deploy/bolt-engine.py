#!/usr/bin/env python3
"""
BOLT Engine — Autonomous Rules Engine for SmarterOS
Monitors system state, executes rules, self-heals, learns.

Deploy: /opt/smarterbot/bolt-engine.py
Run: systemd service every 60s
"""

import os
import json
import time
import httpx
import asyncio
from datetime import datetime, timezone
from pathlib import Path

# ─── CONFIG ───────────────────────────────────────────────
BASE_DIR = Path("/opt/smarterbot")
RULES_FILE = BASE_DIR / "bolt-rules.json"
LOG_FILE = BASE_DIR / "bolt-log.json"
LEADS_FILE = BASE_DIR / "agent/leads.json"

LLM_URL = os.getenv("LLM_URL", "http://127.0.0.1:8000/v1/chat/completions")
TELEGRAM_BOT = os.getenv("TELEGRAM_BOT_TOKEN", "7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6683244662")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://127.0.0.1:8004")
AGENT_URL = os.getenv("AGENT_URL", "http://127.0.0.1:8002")

# ─── STATE ────────────────────────────────────────────────
last_actions = {}  # cooldown tracking
last_leads_count = 0

# ─── HELPERS ──────────────────────────────────────────────
def now():
    return datetime.now(timezone.utc).isoformat()

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}

def save_log(action, detail, status="ok"):
    entry = {"timestamp": now(), "action": action, "detail": detail, "status": status}
    log = load_json(LOG_FILE)
    log.setdefault("actions", []).insert(0, entry)
    log["actions"] = log["actions"][:200]
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2, default=str)

async def send_telegram(msg):
    if not TELEGRAM_BOT or not TELEGRAM_CHAT:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "HTML"}
            )
        return True
    except:
        return False

async def call_llm(prompt):
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(LLM_URL, json={
                "model": "qwen",
                "messages": [
                    {"role": "system", "content": "Eres el agente comercial de SmarterBOT. Responde conciso, amable, enfocado en convertir leads. Máximo 200 caracteres."},
                    {"role": "user", "content": prompt}
                ]
            })
            d = r.json()
            return d["choices"][0]["message"]["content"]
    except:
        return "Gracias por tu interés! Te contactaremos pronto."

def check_webhook():
    try:
        r = httpx.get(f"{WEBHOOK_URL}/health", timeout=3)
        return r.status_code == 200
    except:
        return False

def check_llm():
    try:
        r = httpx.get("http://127.0.0.1:8000/health", timeout=3)
        return r.status_code == 200
    except:
        return False

def check_agent():
    try:
        r = httpx.get(f"{AGENT_URL}/health", timeout=3)
        return r.status_code == 200
    except:
        return False

def get_leads():
    data = load_json(LEADS_FILE)
    return data.get("leads", [])

def count_new_leads():
    global last_leads_count
    data = load_json(LEADS_FILE)
    total = data.get("total", 0)
    new = total - last_leads_count
    if new > 0:
        last_leads_count = total
    return new

def restart_service(name):
    os.system(f"systemctl restart {name}")
    save_log("restart_service", f"Restarted {name}")

# ─── RULES ────────────────────────────────────────────────
DEFAULT_RULES = [
    # Health checks
    {"id": 1, "name": "Webhook health", "if": "webhook_down", "then": "restart_webhook", "priority": "critical"},
    {"id": 2, "name": "LLM health", "if": "llm_down", "then": "alert_telegram", "priority": "high"},
    {"id": 3, "name": "Agent health", "if": "agent_down", "then": "alert_telegram", "priority": "high"},
    
    # Lead processing
    {"id": 10, "name": "New lead detected", "if": "new_lead", "then": "process_lead_llm", "priority": "high"},
    {"id": 11, "name": "Lead → Telegram", "if": "new_lead", "then": "notify_telegram", "priority": "high"},
    
    # Auto-scaling
    {"id": 20, "name": "High traffic", "if": "leads_per_min > 3", "then": "alert_telegram", "priority": "medium"},
    
    # Self-healing
    {"id": 30, "name": "Multiple errors", "if": "consecutive_errors > 3", "then": "alert_telegram", "priority": "critical"},
]

def load_rules():
    try:
        with open(RULES_FILE) as f:
            return json.load(f)
    except:
        return DEFAULT_RULES

def can_execute(rule_id, cooldown=120):
    """Prevent action spam."""
    last = last_actions.get(rule_id, 0)
    if time.time() - last < cooldown:
        return False
    last_actions[rule_id] = time.time()
    return True

# ─── ACTIONS ──────────────────────────────────────────────
async def execute_action(action, context):
    if action == "restart_webhook":
        if can_execute("restart_webhook", 300):
            restart_service("lead-webhook")
            await send_telegram("🔧 Webhook reiniciado (auto-heal)")
    
    elif action == "alert_telegram":
        if can_execute("alert_telegram", 600):
            msg = context.get("alert_msg", "⚠️ Alerta del sistema SmarterBOT")
            await send_telegram(msg)
    
    elif action == "process_lead_llm":
        leads = get_leads()
        if leads:
            latest = leads[0]
            if not latest.get("llm_replied"):
                prompt = f"Nuevo lead: {latest.get('nombre','')} quiere info sobre {latest.get('product','')}. Mensaje: {latest.get('mensaje','')}. Responde como vendedor."
                reply = await call_llm(prompt)
                latest["llm_replied"] = reply
                latest["llm_at"] = now()
                with open(LEADS_FILE, "w") as f:
                    json.dump({"leads": leads, "total": len(leads)}, f, indent=2)
                save_log("llm_reply", f"Lead {latest.get('name','')} → LLM responded")
    
    elif action == "notify_telegram":
        leads = get_leads()
        if leads:
            latest = leads[0]
            if can_execute("notify_telegram", 60):
                msg = f"""🔥 <b>Nuevo Lead SmarterBOT</b>

📦 Producto: {latest.get('product','?')}
👤 Nombre: {latest.get('name','?')}
📧 Email: {latest.get('email','?')}
📱 WhatsApp: {latest.get('phone','?')}
💬 Mensaje: {latest.get('message','')[:100]}
⏰ {now()[:19]}"""
                await send_telegram(msg)

async def evaluate_and_execute(rule, state):
    cond = rule["if"]
    action = rule["then"]
    
    triggered = False
    
    if cond == "webhook_down" and not state.get("webhook_ok"):
        triggered = True
    elif cond == "llm_down" and not state.get("llm_ok"):
        triggered = True
    elif cond == "agent_down" and not state.get("agent_ok"):
        triggered = True
    elif cond == "new_lead" and state.get("new_leads", 0) > 0:
        triggered = True
    elif cond == "leads_per_min > 3" and state.get("new_leads", 0) > 3:
        triggered = True
    
    if triggered:
        save_log("rule_triggered", f"Rule {rule['id']} ({rule['name']}) → {action}")
        await execute_action(action, state)

# ─── MAIN LOOP ────────────────────────────────────────────
async def run_cycle():
    global last_leads_count
    
    # Gather state
    state = {
        "webhook_ok": check_webhook(),
        "llm_ok": check_llm(),
        "agent_ok": check_agent(),
        "new_leads": count_new_leads(),
        "total_leads": load_json(LEADS_FILE).get("total", 0),
        "timestamp": now(),
    }
    
    # Evaluate rules
    rules = load_rules()
    for rule in rules:
        await evaluate_and_execute(rule, state)
    
    return state

async def main():
    print(f"🟡⚫ BOLT Engine starting at {now()}", flush=True)
    print(f"   Rules: {len(DEFAULT_RULES)} | LLM: {LLM_URL}", flush=True)
    
    # Save default rules if not exists
    if not RULES_FILE.exists():
        with open(RULES_FILE, "w") as f:
            json.dump(DEFAULT_RULES, f, indent=2)
    
    # Initialize leads counter
    global last_leads_count
    last_leads_count = load_json(LEADS_FILE).get("total", 0)
    
    while True:
        try:
            state = await run_cycle()
            print(f"[{state['timestamp'][:19]}] webhook={state['webhook_ok']} llm={state['llm_ok']} agent={state['agent_ok']} leads={state['new_leads']} new", flush=True)
        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            save_log("error", str(e), "failed")
        
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
