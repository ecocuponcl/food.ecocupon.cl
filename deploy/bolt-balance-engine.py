#!/usr/bin/env python3
"""
BOLT Engine v3 — Balance Engine (Equilibrium-Based Autonomy)
══════════════════════════════════════════════════════════════
Principio: La crisis no es error → es señal
  Yin (pasivo): observación, logs, datos
  Yang (activo): acciones, reglas, ejecución
  Equilibrio: sistema estable + responsive

No reacciona agresivamente → se auto-regula progresivamente
Cycle: 15s (casi real-time sin matar CPU)

Deploy: /opt/smarterbot/bolt-balance-engine.py
Service: /etc/systemd/system/bolt-balance.service
"""

import os
import sys
import json
import time
import signal
import subprocess
import httpx
from datetime import datetime, timezone
from pathlib import Path

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════
BASE = Path("/opt/smarterbot")
LEADS = BASE / "agent/leads.json"
LOG = BASE / "bolt-balance-log.json"
STATUS = BASE / "status-balance.json"

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "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")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TG_BOT = os.getenv("TELEGRAM_BOT_TOKEN", "7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6683244662")

INTERVAL = 15  # seconds
running = True

def shutdown(sig, frame):
    global running
    running = False
    log_action("shutdown", f"Signal {sig}", "info")
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)

# ═══════════════════════════════════════════════════════════
# SENSOR — Lee señales, no solo errores
# ═══════════════════════════════════════════════════════════
def check_http(url, timeout=3):
    try:
        r = httpx.get(url, timeout=timeout, follow_redirects=False)
        return True, r.status_code
    except:
        return False, 0

def get_leads_data():
    try:
        with open(LEADS) as f:
            data = json.load(f)
        leads = data.get("leads", []) if isinstance(data, dict) else data
        total = data.get("total", len(leads)) if isinstance(data, dict) else len(leads)
        return leads, total
    except:
        return [], 0

def get_recent_leads(minutes=5):
    leads, _ = get_leads_data()
    cutoff = datetime.now(timezone.utc).timestamp() - (minutes * 60)
    return [l for l in leads if datetime.fromisoformat(l.get("timestamp", "1970-01-01")).timestamp() > cutoff]

def get_last_errors(count=10):
    try:
        with open(LOG) as f:
            data = json.load(f)
        errors = [a for a in data.get("actions", []) if a.get("status") == "failed"]
        return errors[:count]
    except:
        return []

# ═══════════════════════════════════════════════════════════
# EQUILIBRIUM — Estado como balance dinámico
# ═══════════════════════════════════════════════════════════
def compute_equilibrium():
    """
    Compute system balance as Yin/Yang equilibrium.
    
    Returns a balance state dict with scores 0-100.
    """
    # ─── YIN: Observation signals ───
    webhook_ok, wh_code = check_http("http://127.0.0.1:8004/health")
    llm_ok, _ = check_http("http://127.0.0.1:8000/health")
    agent_ok, _ = check_http("http://127.0.0.1:8002/health")
    n8n_ok, _ = check_http("http://127.0.0.1:5678/healthz")
    caddy_ok, _ = check_http("http://127.0.0.1:2019/config/")
    
    health_score = sum([webhook_ok, llm_ok, agent_ok, n8n_ok, caddy_ok]) / 5 * 100
    
    # ─── YANG: Action signals ───
    leads, total_leads = get_leads_data()
    recent_leads = get_recent_leads(5)
    leads_rate = len(recent_leads) / 5  # leads per minute (5 min window)
    
    errors = get_last_errors(10)
    error_count = len([e for e in errors if e.get("timestamp", "").startswith(
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")
    )])
    error_rate = error_count / max(total_leads, 1)
    
    # Unprocessed leads (work pending)
    unprocessed = sum(1 for l in leads if not l.get("llm_replied"))
    
    # ─── Balance computation ───
    # Optimal: leads_rate >= 0.5, error_rate < 0.1, unprocessed < 5
    flow_score = min(100, leads_rate * 100) if leads_rate > 0 else 0
    stress_score = max(0, 100 - (error_rate * 500))  # High errors = high stress
    yin_score = (100 - min(100, unprocessed * 20))  # Many unprocessed = low yin (observation gap)
    yang_score = health_score  # Services healthy = capacity for action
    
    # Overall balance: geometric mean (penalizes extremes)
    scores = [s for s in [flow_score, stress_score, yin_score, yang_score] if s > 0]
    balance_score = (1.0)
    for s in scores:
        balance_score *= (s / 100.0)
    balance_score = (balance_score ** (1.0 / max(len(scores), 1))) * 100
    
    # Determine state
    if balance_score >= 80:
        state = "balanced"
    elif balance_score >= 50:
        state = "adjusting"
    elif balance_score >= 20:
        state = "stressed"
    else:
        state = "critical"
    
    return {
        "balance": state,
        "balance_score": round(balance_score, 1),
        
        # Yin (observation)
        "yin_score": round(yin_score, 1),
        "unprocessed_leads": unprocessed,
        "total_leads": total_leads,
        
        # Yang (action)
        "yang_score": round(yang_score, 1),
        "health_score": round(health_score, 1),
        "services": {
            "webhook": webhook_ok,
            "llm": llm_ok,
            "agent": agent_ok,
            "n8n": n8n_ok,
            "caddy": caddy_ok,
        },
        
        # Flow
        "flow_score": round(flow_score, 1),
        "leads_rate": round(leads_rate, 2),
        "recent_leads_5min": len(recent_leads),
        
        # Stress
        "stress_score": round(stress_score, 1),
        "error_rate": round(error_rate, 3),
        "errors_this_hour": error_count,
        
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

# ═══════════════════════════════════════════════════════════
# AUTO-REGULATION — Ajuste progresivo, no reacción
# ═══════════════════════════════════════════════════════════
cooldowns = {}

def can_act(action, cooldown=300):
    """Prevent action spam — progressive regulation."""
    if action in cooldowns and time.time() - cooldowns[action] < cooldown:
        return False
    cooldowns[action] = time.time()
    return True

def log_action(action, detail, status="info"):
    """Log to balance log file."""
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "action": action, "detail": detail[:200], "status": status}
    try:
        with open(LOG) as f:
            data = json.load(f)
    except:
        data = {"actions": []}
    data.setdefault("actions", []).insert(0, entry)
    data["actions"] = data["actions"][:500]
    with open(LOG, "w") as f:
        json.dump(data, f, indent=2, default=str)

async def send_telegram(msg):
    """Send Telegram alert."""
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
    except:
        return False

async def call_llm(nombre, producto, mensaje):
    """Get AI response via OpenRouter."""
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(OPENROUTER_URL, json={
                "model": "qwen/qwen-turbo",
                "messages": [
                    {"role": "system", "content": "Eres el agente comercial de SmarterBOT. Responde conciso, profesional, enfocado en convertir. Max 150 chars. Incluye CTA."},
                    {"role": "user", "content": f"Lead: {nombre}. Producto: {producto}. Mensaje: {mensaje}. Responde como vendedor."}
                ],
                "max_tokens": 200
            }, headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "HTTP-Referer": "https://smarterbot.store",
                "X-Title": "SmarterBOT"
            }, timeout=15)
            d = r.json()
            return d["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Gracias {nombre}! Te contactaremos pronto con info sobre {producto}."

def restart_service(name):
    """Restart a systemd service — gentle action."""
    try:
        result = subprocess.run(["systemctl", "restart", name], timeout=10, capture_output=True)
        time.sleep(2)
        check = subprocess.run(["systemctl", "is-active", name], capture_output=True, text=True, timeout=5)
        ok = check.stdout.strip() == "active"
        log_action(f"restart_{name}", f"{'OK' if ok else 'FAILED'}", "ok" if ok else "failed")
        return ok
    except Exception as e:
        log_action(f"restart_{name}", str(e), "failed")
        return False

def process_lead(lead):
    """Process a lead with LLM."""
    nombre = lead.get("name", "Cliente")
    producto = lead.get("product", "general")
    mensaje = lead.get("message", "")
    
    import asyncio
    reply = asyncio.get_event_loop().run_until_complete(call_llm(nombre, producto, mensaje))
    lead["llm_replied"] = reply
    lead["llm_at"] = datetime.now(timezone.utc).isoformat()
    
    # Save
    try:
        with open(LEADS) as f:
            data = json.load(f)
        leads = data.get("leads", []) if isinstance(data, dict) else data
        for i, l in enumerate(leads):
            if l.get("id") == lead.get("id"):
                leads[i] = lead
                break
        if isinstance(data, dict):
            data["leads"] = leads
            data["total"] = len(leads)
        with open(LEADS, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log_action("save_lead_error", str(e), "failed")
    
    log_action("lead_processed", f"{nombre} → {producto}", "ok")
    
    # Telegram notification
    import asyncio
    msg = f"🔥 <b>Nuevo Lead</b>\n📦 {producto}\n👤 {nombre}\n📱 {lead.get('phone','')}\n💬 {mensaje[:80]}\n\n🤖 <b>IA:</b>\n{reply}"
    asyncio.get_event_loop().run_until_complete(send_telegram(msg))

# ═══════════════════════════════════════════════════════════
# BALANCE ENGINE — Auto-regulación inteligente
# ═══════════════════════════════════════════════════════════
def regulate(balance):
    """
    Progressive auto-regulation based on equilibrium state.
    Not reactive — adjusts gradually to restore balance.
    """
    actions = []
    state = balance["balance"]
    
    # ─── CRITICAL: Immediate action needed ───
    if state == "critical":
        # Services down — restart most critical first
        if not balance["services"]["webhook"] and can_act("restart_webhook_critical", 120):
            ok = restart_service("lead-webhook")
            actions.append(f"restart_webhook={'ok' if ok else 'fail'}")
        
        if not balance["services"]["llm"] and can_act("alert_llm_critical", 300):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                send_telegram("🚨 <b>CRÍTICO</b>\nLLM caído — sistema sin IA")
            )
            actions.append("alert_llm_critical")
    
    # ─── STRESSED: Progressive adjustment ───
    elif state == "stressed":
        # High error rate — check and adjust
        if balance["error_rate"] > 0.3 and can_act("check_errors", 600):
            errors = get_last_errors(5)
            error_types = set(e.get("action", "unknown") for e in errors)
            log_action("error_analysis", f"Types: {error_types}", "warn")
            actions.append("analyzed_errors")
        
        # Unprocessed leads building up — process them
        if balance["unprocessed_leads"] > 3 and can_act("process_backlog", 60):
            leads, _ = get_leads_data()
            unprocessed = [l for l in leads[:5] if not l.get("llm_replied")]
            for lead in unprocessed:
                process_lead(lead)
                actions.append(f"process_{lead.get('name','?')}")
        
        # Webhook degraded — gentle restart
        if not balance["services"]["webhook"] and can_act("restart_webhook_gentle", 300):
            ok = restart_service("lead-webhook")
            actions.append(f"restart_webhook={'ok' if ok else 'fail'}")
    
    # ─── ADJUSTING: Fine-tuning ───
    elif state == "adjusting":
        # Process any unprocessed leads
        if balance["unprocessed_leads"] > 0 and can_act("process_pending", 30):
            leads, _ = get_leads_data()
            unprocessed = [l for l in leads[:3] if not l.get("llm_replied")]
            for lead in unprocessed:
                process_lead(lead)
                actions.append(f"process_{lead.get('name','?')}")
    
    # ─── BALANCED: Observe and log ───
    # No action needed — system is in equilibrium
    # Yin mode: just observe and log
    
    return actions

# ═══════════════════════════════════════════════════════════
# STATUS — Control Tower output
# ═══════════════════════════════════════════════════════════
def write_status(balance, actions):
    """Write balance status to file for Control Tower UI."""
    status = {
        "version": "bolt-v3-balance-engine",
        "balance": balance["balance"],
        "balance_score": balance["balance_score"],
        "yin_score": balance["yin_score"],
        "yang_score": balance["yang_score"],
        "flow_score": balance["flow_score"],
        "stress_score": balance["stress_score"],
        "services": balance["services"],
        "leads_total": balance["total_leads"],
        "leads_rate": balance["leads_rate"],
        "unprocessed": balance["unprocessed_leads"],
        "error_rate": balance["error_rate"],
        "actions_last_run": actions,
        "timestamp": balance["timestamp"],
    }
    with open(STATUS, "w") as f:
        json.dump(status, f, indent=2)

# ═══════════════════════════════════════════════════════════
# MAIN LOOP
# ═══════════════════════════════════════════════════════════
def main():
    print(f"🟡⚫ BOLT v3 — Balance Engine (Equilibrium-Based)", flush=True)
    print(f"   Yin (observe) + Yang (act) = Equilibrium", flush=True)
    print(f"   Cycle: {INTERVAL}s | LLM: OpenRouter", flush=True)
    print(f"   Telegram: {'SET' if TG_BOT and TG_CHAT else 'NOT SET'}", flush=True)
    print()
    
    cycle = 0
    while running:
        cycle += 1
        try:
            # 1. SENSOR: Read system state
            balance = compute_equilibrium()
            
            # 2. REGULATE: Progressive auto-adjustment
            actions = regulate(balance)
            
            # 3. STATUS: Write to Control Tower
            write_status(balance, actions)
            
            # 4. LOG: Print equilibrium state
            action_str = f" → {actions}" if actions else ""
            print(f"[{balance['timestamp'][:19]}] cycle={cycle} "
                  f"balance={balance['balance']}({balance['balance_score']}) "
                  f"yin={balance['yin_score']} yang={balance['yang_score']} "
                  f"flow={balance['flow_score']} stress={balance['stress_score']} "
                  f"leads={balance['total_leads']} rate={balance['leads_rate']:.2f}/min "
                  f"errors={balance['errors_this_hour']}{action_str}", flush=True)
            
        except Exception as e:
            print(f"ERROR cycle {cycle}: {e}", flush=True)
            log_action("cycle_error", str(e), "failed")
        
        # Interruptible wait
        for _ in range(INTERVAL * 2):
            if not running:
                break
            time.sleep(0.5)
    
    print("BOLT Balance Engine stopped.", flush=True)

if __name__ == "__main__":
    main()
