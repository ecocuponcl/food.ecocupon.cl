#!/usr/bin/env python3
"""
BOLT Engine v2 — Autonomous System (Sensor + Actor + Loop)
═════════════════════════════════════════════════════════════
Detecta → Decide → Ejecuta → Valida → Aprende
Cycle: 15s (casi real-time sin matar CPU)

Deploy: /opt/smarterbot/bolt-engine.py
Service: /etc/systemd/system/bolt.service
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
LOG = BASE / "bolt-log.json"
STATUS = BASE / "status.json"

LLM = "http://127.0.0.1:8000/v1/chat/completions"
TG_BOT = os.getenv("TELEGRAM_BOT_TOKEN", "7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6683244662")

INTERVAL = 15  # seconds
MAX_LEADS_PER_CYCLE = 10

running = True

def shutdown(sig, frame):
    global running
    running = False
    log("shutdown", f"Received signal {sig}")
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)

# ═══════════════════════════════════════════════════════════
# SENSOR — Estado real del sistema
# ═══════════════════════════════════════════════════════════
def check_http(url, timeout=3):
    try:
        r = httpx.get(url, timeout=timeout, follow_redirects=False)
        return r.status_code < 500, r.status_code
    except:
        return False, 0

def count_leads():
    try:
        with open(LEADS) as f:
            return len(json.load(f).get("leads", []))
    except:
        return 0

def count_errors():
    try:
        with open(LOG) as f:
            data = json.load(f)
            errors = [a for a in data.get("actions", []) if a.get("status") == "failed"]
            return len([e for e in errors if e.get("timestamp", "").startswith(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H"))])
    except:
        return 0

def get_unprocessed_leads():
    """Get leads that don't have llm_replied yet."""
    try:
        with open(LEADS) as f:
            data = json.load(f)
        leads = data.get("leads", [])
        return [l for l in leads[:MAX_LEADS_PER_CYCLE] if not l.get("llm_replied")]
    except:
        return []

def get_system_state():
    webhook_ok, code = check_http("http://127.0.0.1:8004/health")
    llm_ok, _ = check_http("http://127.0.0.1:8000/health")
    agent_ok, _ = check_http("http://127.0.0.1:8002/health")
    n8n_ok, _ = check_http("http://127.0.0.1:5678/healthz")
    caddy_ok, _ = check_http("http://127.0.0.1:2019/config/")

    return {
        "webhook_ok": webhook_ok,
        "webhook_code": code,
        "llm_ok": llm_ok,
        "agent_ok": agent_ok,
        "n8n_ok": n8n_ok,
        "caddy_ok": caddy_ok,
        "total_leads": count_leads(),
        "unprocessed_leads": len(get_unprocessed_leads()),
        "errors_last_hour": count_errors(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

# ═══════════════════════════════════════════════════════════
# ACTOR — Ejecuta acciones reales
# ═══════════════════════════════════════════════════════════
def restart_service(name):
    """Restart a systemd service and verify."""
    try:
        subprocess.run(["systemctl", "restart", name], timeout=10)
        time.sleep(2)
        result = subprocess.run(["systemctl", "is-active", name], capture_output=True, text=True, timeout=5)
        ok = result.stdout.strip() == "active"
        log(f"restart_{name}", f"Restarted {name}: {'OK' if ok else 'FAILED'}", "ok" if ok else "failed")
        return ok
    except Exception as e:
        log(f"restart_{name}", str(e), "failed")
        return False

def call_llm(nombre, producto, mensaje):
    """Get AI response for lead."""
    try:
        r = httpx.post(LLM, json={
            "model": "qwen",
            "messages": [
                {"role": "system", "content": "Eres el agente comercial de SmarterBOT. Responde conciso, profesional, enfocado en convertir. Máximo 200 caracteres. Incluye CTA."},
                {"role": "user", "content": f"Lead: {nombre}. Producto: {producto}. Mensaje: {mensaje}. Responde como vendedor."}
            ]
        }, timeout=15)
        d = r.json()
        return d["choices"][0]["message"]["content"]
    except Exception as e:
        log("llm_error", str(e)[:100], "failed")
        return f"Gracias {nombre}! Te contactaremos pronto con info sobre {producto}."

def send_telegram(msg):
    """Send Telegram alert."""
    if not TG_BOT or not TG_CHAT:
        return False
    try:
        httpx.post(f"https://api.telegram.org/bot{TG_BOT}/sendMessage",
            json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"}, timeout=10)
        return True
    except:
        return False

def process_lead(lead):
    """Process a single lead: LLM → save → alert."""
    nombre = lead.get("name", "Cliente")
    producto = lead.get("product", "general")
    mensaje = lead.get("message", "")

    reply = call_llm(nombre, producto, mensaje)
    lead["llm_replied"] = reply
    lead["llm_at"] = datetime.now(timezone.utc).isoformat()

    # Save back
    try:
        with open(LEADS) as f:
            data = json.load(f)
        for i, l in enumerate(data.get("leads", [])):
            if l.get("id") == lead.get("id"):
                data["leads"][i] = lead
                break
        with open(LEADS, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log("save_lead_error", str(e), "failed")

    # Telegram alert
    msg = f"🔥 <b>Nuevo Lead</b>\n📦 {producto}\n👤 {nombre}\n📱 {lead.get('phone','')}\n💬 {mensaje[:80]}\n\n🤖 <b>Respuesta LLM:</b>\n{reply}"
    send_telegram(msg)

    log("lead_processed", f"{nombre} → {producto}", "ok")

# ═══════════════════════════════════════════════════════════
# RULES — Decisiones automáticas
# ═══════════════════════════════════════════════════════════
cooldowns = {}

def can_run(action, cooldown=300):
    if action in cooldowns and time.time() - cooldowns[action] < cooldown:
        return False
    cooldowns[action] = time.time()
    return True

def run_rules(state):
    """Evaluate and execute rules based on state."""
    actions_taken = []

    # Rule 1: Webhook down → restart
    if not state["webhook_ok"]:
        if can_run("restart_webhook", 300):
            ok = restart_service("lead-webhook")
            if not ok:
                send_telegram("🚨 <b>CRÍTICO</b>\nWebhook down y no pudo reiniciar")
            else:
                send_telegram("🔧 Auto-heal: Webhook reiniciado exitosamente")
            actions_taken.append(f"restart_webhook({'ok' if ok else 'fail'})")

    # Rule 2: LLM down → alert
    if not state["llm_ok"]:
        if can_run("alert_llm", 600):
            send_telegram("⚠️ <b>LLM DOWN</b>\nEl agente IA no responde")
            actions_taken.append("alert_llm_down")

    # Rule 3: Agent down → alert
    if not state["agent_ok"]:
        if can_run("alert_agent", 600):
            send_telegram("⚠️ <b>Agent DOWN</b>\nMonitor de servicios caído")
            actions_taken.append("alert_agent_down")

    # Rule 4: New leads → process with LLM
    if state["unprocessed_leads"] > 0:
        leads = get_unprocessed_leads()
        for lead in leads:
            process_lead(lead)
            actions_taken.append(f"process_lead_{lead.get('name','?')}")

    # Rule 5: High error rate → alert
    if state["errors_last_hour"] > 5:
        if can_run("alert_errors", 1800):
            send_telegram(f"🚨 <b>Alta tasa de errores</b>\n{state['errors_last_hour']} errores en la última hora")
            actions_taken.append("alert_high_errors")

    return actions_taken

# ═══════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════
def log(action, detail, status="ok"):
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

# ═══════════════════════════════════════════════════════════
# STATUS ENDPOINT (Control Tower)
# ═══════════════════════════════════════════════════════════
def write_status(state, actions):
    """Write current status to file for Control Tower UI."""
    status = {
        "status": "ok" if state["webhook_ok"] and state["llm_ok"] else "degraded",
        "webhook": state["webhook_ok"],
        "llm": state["llm_ok"],
        "agent": state["agent_ok"],
        "n8n": state["n8n_ok"],
        "caddy": state["caddy_ok"],
        "leads_total": state["total_leads"],
        "unprocessed": state["unprocessed_leads"],
        "errors_last_hour": state["errors_last_hour"],
        "actions_last_run": actions,
        "timestamp": state["timestamp"],
        "version": "bolt-v2-autonomous",
    }
    with open(STATUS, "w") as f:
        json.dump(status, f, indent=2)

# ═══════════════════════════════════════════════════════════
# MAIN LOOP
# ═══════════════════════════════════════════════════════════
def main():
    print(f"🟡⚫ BOLT Engine v2 — Autonomous System", flush=True)
    print(f"   Sensor → Actor → Loop (15s cycle)", flush=True)
    print(f"   LLM: {LLM}", flush=True)
    print(f"   Telegram: {'SET' if TG_BOT and TG_CHAT else 'NOT SET'}", flush=True)
    print()

    cycle = 0
    while running:
        cycle += 1
        try:
            # SENSOR
            state = get_system_state()

            # ACTOR → RULES
            actions = run_rules(state)

            # STATUS
            write_status(state, actions)

            # LOG
            status_str = "ok" if state["webhook_ok"] and state["llm_ok"] else "DEGRADED"
            action_str = f" actions={actions}" if actions else ""
            print(f"[{state['timestamp'][:19]}] cycle={cycle} {status_str} "
                  f"webhook={state['webhook_ok']} llm={state['llm_ok']} "
                  f"leads={state['total_leads']} unproc={state['unprocessed_leads']}"
                  f" errors={state['errors_last_hour']}{action_str}", flush=True)

        except Exception as e:
            print(f"ERROR cycle {cycle}: {e}", flush=True)
            log("cycle_error", str(e), "failed")

        # WAIT (interruptible)
        for _ in range(INTERVAL * 2):
            if not running:
                break
            time.sleep(0.5)

    print("BOLT Engine stopped.", flush=True)

if __name__ == "__main__":
    main()
