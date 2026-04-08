#!/usr/bin/env python3
"""
SmarterBOT Agent-Local v2.2.0-fused
══════════════════════════════════════
Fusión: v2.0.0 (base estable) + v2.1.0 (multi-tenant)
  - 14 servicios monitoreados
  - Multi-tenant con Telegram routing
  - Auto-recovery con reglas
  - Supabase logging persistente
  - Conversion tracking
  - FastAPI :8002

Runtime: Python directo (systemd), NO Docker
"""

import asyncio
import httpx
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# ─── PATHS ────────────────────────────────────────────────
BASE_DIR = Path("/opt/smarterbot/agent")
TENANTS_FILE = BASE_DIR / "tenants.json"
RECOVERY_RULES_FILE = BASE_DIR / "recovery_rules.json"
RECOVERY_LOG_FILE = BASE_DIR / "recovery_log.json"
CONVERSIONS_FILE = BASE_DIR / "conversions.json"

# ─── ENV SECRETS ──────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rjfcmmzjlguiititkmyh.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
DEFAULT_TG_BOT = os.getenv("TELEGRAM_BOT_TOKEN", "7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc")
DEFAULT_TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6683244662")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))

# ─── 14 SERVICES ─────────────────────────────────────────
SERVICES = {
    # Core infrastructure
    "agent":          {"url": "http://127.0.0.1:9001/health",     "timeout": 3,  "tenant": "ecocupon"},
    "food_odoo":      {"url": "http://127.0.0.1:8070",           "timeout": 5,  "tenant": "ecocupon"},
    "food_agent":     {"url": "http://127.0.0.1:9004/health",    "timeout": 3,  "tenant": "ecocupon"},
    "qr":             {"url": "http://127.0.0.1:9004/health",    "timeout": 3,  "tenant": "ecocupon"},
    # Smarter infra
    "llm":            {"url": "http://127.0.0.1:8000/health",    "timeout": 5,  "tenant": "smarter"},
    "llm_middleware": {"url": "http://127.0.0.1:8001/health",    "timeout": 5,  "tenant": "smarter"},
    "n8n":            {"url": "http://127.0.0.1:5678/healthz",   "timeout": 5,  "tenant": "smarter"},
    "caddy":          {"url": "http://127.0.0.1:2019/config/",   "timeout": 2,  "tenant": "smarter"},
    "picoclaw":       {"url": "http://127.0.0.1:18792/health",   "timeout": 3,  "tenant": "smarter"},
    "chatwoot":       {"url": "http://127.0.0.1:3000/",          "timeout": 5,  "tenant": "smarter"},
    "odoo19":         {"url": "http://127.0.0.1:8069",           "timeout": 5,  "tenant": "smarter"},
    # Data stores (TCP)
    "postgres":       {"type": "tcp", "host": "127.0.0.1", "port": 5432, "timeout": 2, "tenant": "smarter"},
    "redis":          {"type": "tcp", "host": "127.0.0.1", "port": 6379, "timeout": 2, "tenant": "smarter"},
    # Bolt dashboard
    "bolt":           {"url": "http://127.0.0.1:8501/healthz",   "timeout": 5,  "tenant": "smarter"},
}

# ─── STATE ────────────────────────────────────────────────
_cached_status = None
_last_check = None
_recovery_history = []
_conversions = {"total": 0, "by_tenant": {}, "recent": []}
_shutdown = False

# ─── HELPERS ──────────────────────────────────────────────
def load_json(path: Path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default or {}

def save_json(path: Path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)

def load_tenants() -> dict:
    data = load_json(TENANTS_FILE, {})
    if "tenants" not in data:
        # Flat format or missing — create default
        return {
            "default_tenant": "smarter",
            "tenants": {
                "smarter": {
                    "name": "Smarter SPA",
                    "bot_token": DEFAULT_TG_BOT,
                    "chat_id": DEFAULT_TG_CHAT,
                    "services": [s for s, c in SERVICES.items() if c.get("tenant") == "smarter"],
                    "alert_enabled": True,
                    "alert_cooldown_sec": 1800,
                    "max_retries": 3,
                    "recovery_enabled": True,
                },
                "ecocupon": {
                    "name": "Ecocupon / Ecocanasta",
                    "bot_token": os.getenv("ECOCOUPON_BOT_TOKEN", ""),
                    "chat_id": os.getenv("ECOCOUPON_CHAT_ID", ""),
                    "services": [s for s, c in SERVICES.items() if c.get("tenant") == "ecocupon"],
                    "alert_enabled": bool(os.getenv("ECOCOUPON_BOT_TOKEN")),
                    "alert_cooldown_sec": 1800,
                    "max_retries": 3,
                    "recovery_enabled": True,
                },
                "food": {
                    "name": "Food Platform",
                    "bot_token": os.getenv("FOOD_BOT_TOKEN", ""),
                    "chat_id": os.getenv("FOOD_CHAT_ID", ""),
                    "services": ["food_odoo", "food_agent"],
                    "alert_enabled": bool(os.getenv("FOOD_BOT_TOKEN")),
                    "alert_cooldown_sec": 1800,
                    "max_retries": 3,
                    "recovery_enabled": True,
                },
            }
        }
    return data

def get_tenant_for_service(service_name: str) -> str:
    cfg = SERVICES.get(service_name, {})
    return cfg.get("tenant", "smarter")

def get_tenant_bot(tenant: str) -> tuple:
    """Return (bot_token, chat_id) for a tenant."""
    tenants = load_tenants()
    t = tenants.get("tenants", {}).get(tenant, {})
    return t.get("bot_token", ""), t.get("chat_id", "")

# ─── FASTAPI ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    _recovery_history[:] = load_json(RECOVERY_LOG_FILE, {}).get("actions", [])
    _conversions.update(load_json(CONVERSIONS_FILE, _conversions))
    task = asyncio.create_task(background_loop())
    yield
    global _shutdown
    _shutdown = True
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="SmarterBOT Agent-Local", version="2.2.0-fused", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "smarterbot-agent-local",
        "version": "2.2.0-fused",
        "uptime_sec": int(time.monotonic()),
        "last_check": _last_check,
        "services_count": len(SERVICES),
        "tenants": list(load_tenants().get("tenants", {}).keys()),
    }

@app.get("/status.json")
@app.get("/status")
@app.get("/services")
async def get_status():
    if _cached_status:
        return _cached_status
    return {"status": "initializing", "message": "First check pending", "version": "2.2.0-fused"}

@app.get("/tenants.json")
@app.get("/tenants")
async def get_tenants():
    tenants = load_tenants()
    # Hide tokens from public endpoint
    safe = json.loads(json.dumps(tenants))
    for t in safe.get("tenants", {}).values():
        if t.get("bot_token") and t["bot_token"] != "PLACEHOLDER_REPLACE_ME":
            t["bot_token"] = "SET (len=" + str(len(t["bot_token"])) + ")"
        else:
            t["bot_token"] = "NOT SET"
    return safe

@app.get("/conversions.json")
@app.get("/conversions")
async def get_conversions():
    return _conversions

@app.post("/conversion")
async def post_conversion(request: Request):
    """Register a new conversion/lead (called by n8n)."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    conversion = {
        "id": _conversions["total"] + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phone": body.get("phone", ""),
        "tenant": body.get("tenant", "smarter"),
        "message": body.get("message", ""),
        "source": body.get("source", "webhook"),
        "odoo_lead_id": body.get("odoo_lead_id"),
        "event_type": "conversion",
    }

    _conversions["total"] += 1
    tenant = conversion["tenant"]
    _conversions["by_tenant"][tenant] = _conversions["by_tenant"].get(tenant, 0) + 1
    _conversions["recent"].insert(0, conversion)
    _conversions["recent"] = _conversions["recent"][:100]
    _conversions["last_updated"] = datetime.now(timezone.utc).isoformat()
    save_json(CONVERSIONS_FILE, _conversions)

    return {"status": "ok", "conversion_id": conversion["id"]}

@app.get("/recovery.json")
@app.get("/recovery")
async def get_recovery():
    return {"actions": _recovery_history[-50:]}

# ─── CHECK FUNCTIONS ──────────────────────────────────────
async def check_http(url: str, timeout: int) -> dict:
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, follow_redirects=False)
            latency = int((time.monotonic() - start) * 1000)
            return {"status": "ok", "latency_ms": latency, "http_code": resp.status_code}
    except Exception as e:
        latency = int((time.monotonic() - start) * 1000)
        return {"status": "down", "latency_ms": latency, "error": str(e)[:100]}

async def check_tcp(host: str, port: int, timeout: int) -> dict:
    start = time.monotonic()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        latency = int((time.monotonic() - start) * 1000)
        return {"status": "ok", "latency_ms": latency}
    except Exception as e:
        latency = int((time.monotonic() - start) * 1000)
        return {"status": "down", "latency_ms": latency, "error": str(e)[:100]}

async def check_all_services() -> dict:
    tasks = {}
    for name, cfg in SERVICES.items():
        if cfg.get("type") == "tcp":
            tasks[name] = asyncio.create_task(check_tcp(cfg["host"], cfg["port"], cfg["timeout"]))
        elif cfg.get("url"):
            tasks[name] = asyncio.create_task(check_http(cfg["url"], cfg["timeout"]))
        else:
            tasks[name] = asyncio.create_task(asyncio.sleep(0, result={"status": "unknown", "latency_ms": 0}))

    results = {name: await task for name, task in tasks.items()}
    overall = "ok"
    for name, r in results.items():
        if r["status"] == "down":
            overall = "degraded"
            break
    return {
        "status": overall,
        "services": results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.2.0-fused",
    }

# ─── AUTO-RECOVERY ────────────────────────────────────────
def should_attempt_recovery(service: str) -> bool:
    rules = load_json(RECOVERY_RULES_FILE, {})
    policy = rules.get("policy", {})
    cooldown = policy.get("cooldown_after_success_sec", 300)
    max_retries = policy.get("max_retries", 3)

    recent = [a for a in _recovery_history
              if a.get("service") == service
              and (datetime.now(timezone.utc) - datetime.fromisoformat(a["timestamp"])).total_seconds() < cooldown * 2]

    if len(recent) >= max_retries:
        return False

    svc_rules = rules.get("services", {}).get(service, {})
    if not svc_rules.get("auto_recover", False):
        return False

    return True

async def attempt_recovery(service: str) -> dict:
    rules = load_json(RECOVERY_RULES_FILE, {})
    svc_rules = rules.get("services", {}).get(service, {})

    if not svc_rules.get("auto_recover", False):
        return {"service": service, "result": "skipped", "reason": "auto_recover disabled"}

    if not should_attempt_recovery(service):
        return {"service": service, "result": "skipped", "reason": "cooldown/max_retries"}

    cmd = svc_rules.get("restart_command", "")
    if not cmd:
        return {"service": service, "result": "failed", "reason": "no restart_command"}

    start = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        duration = int((time.monotonic() - start) * 1000)

        if proc.returncode == 0:
            await asyncio.sleep(2)
            status_cmd = svc_rules.get("status_command", "")
            if status_cmd:
                verify = await asyncio.create_subprocess_shell(status_cmd, stdout=asyncio.subprocess.PIPE)
                out, _ = await verify.communicate()
                running = verify.returncode == 0 and b"active" in out.lower()
            else:
                running = True
            result = "success" if running else "partial"
        else:
            result = "failed"

        action = {
            "service": service,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": cmd,
            "result": result,
            "duration_ms": duration,
            "return_code": proc.returncode,
        }
        _recovery_history.append(action)
        save_json(RECOVERY_LOG_FILE, {"actions": _recovery_history[-100:]})
        return action

    except Exception as e:
        duration = int((time.monotonic() - start) * 1000)
        action = {
            "service": service,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": cmd,
            "result": "error",
            "error": str(e)[:200],
            "duration_ms": duration,
        }
        _recovery_history.append(action)
        save_json(RECOVERY_LOG_FILE, {"actions": _recovery_history[-100:]})
        return action

# ─── TELEGRAM ALERTS ──────────────────────────────────────
async def send_telegram(message: str, bot_token: str = "", chat_id: str = ""):
    if not bot_token:
        bot_token = DEFAULT_TG_BOT
    if not chat_id:
        chat_id = DEFAULT_TG_CHAT
    if not bot_token or not chat_id:
        return
    # Escape HTML special chars in error messages
    safe_msg = message.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": safe_msg, "parse_mode": "HTML"}
            )
    except Exception:
        pass

async def alert_tenant(service: str, status: str, result: dict = None):
    """Send alert to the correct tenant bot."""
    tenant = get_tenant_for_service(service)
    bot_token, chat_id = get_tenant_bot(tenant)
    if not bot_token or not chat_id:
        return  # Tenant not configured, skip silently

    if result and result.get("result") == "success":
        msg = f"🔧 <b>AUTO-RECOVERY</b>\n✅ {service.upper()} recuperado\n⏱ {result.get('duration_ms', '?')}ms\n⏰ {datetime.now(timezone.utc).strftime('%H:%M')} UTC"
    else:
        error = result.get("error", "sin respuesta") if result else "sin respuesta"
        msg = f"🚨 <b>SERVICIO DOWN</b>\n❌ {service.upper()}: {error}\n🔧 Recovery: {result.get('result', 'N/A') if result else 'N/A'}\n⏰ {datetime.now(timezone.utc).strftime('%H:%M')} UTC"

    await send_telegram(msg, bot_token, chat_id)

# ─── SUPABASE LOGGING ─────────────────────────────────────
async def log_to_supabase(service: str, status: str, latency: int, details: dict):
    if not SUPABASE_KEY:
        return
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"{SUPABASE_URL}/rest/v1/service_status_logs",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                json={"service": service, "status": status, "latency_ms": latency, "details": details},
            )
    except Exception:
        pass  # Don't fail monitoring if logging fails

# ─── BACKGROUND LOOP ──────────────────────────────────────
async def background_loop():
    global _cached_status, _last_check
    _recovery_history[:] = load_json(RECOVERY_LOG_FILE, {}).get("actions", [])

    while not _shutdown:
        try:
            status = await check_all_services()
            _cached_status = status
            _last_check = status["timestamp"]

            for name, result in status["services"].items():
                # Log to Supabase
                await log_to_supabase(name, result["status"], result.get("latency_ms", 0), result)

                # Auto-recovery + alert if down
                if result["status"] == "down":
                    recovery = await attempt_recovery(name)
                    await alert_tenant(name, result["status"], recovery)

        except Exception as e:
            print(f"[ERROR] background_loop: {e}", flush=True)

        await asyncio.sleep(CHECK_INTERVAL)

# ─── ENTRY POINT ──────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    tenants = load_tenants()
    tenant_names = list(tenants.get("tenants", {}).keys())
    print(f"🟡⚫ SmarterBOT Agent-Local v2.2.0-fused", flush=True)
    print(f"   Services: {len(SERVICES)} | Tenants: {tenant_names} | Interval: {CHECK_INTERVAL}s", flush=True)
    print(f"   Supabase: {'SET' if SUPABASE_KEY else 'NOT SET'}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="warning")
