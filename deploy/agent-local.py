#!/usr/bin/env python3
"""
agent-local.py — Agente Local Unificado EcoCupon
Fusiona: status-monitor + alert-checker + auto-recovery + status-aggregator

Endpoints FastAPI :8002:
  GET /status.json   → Estado de todos los servicios
  GET /recovery.json → Historial de auto-recovery
  GET /health        → Health del agente

Background loop (cada 60s):
  1. Check todos los servicios
  2. Log a Supabase
  3. Si down → auto-recovery
  4. Si recovery falla → alerta Telegram
  5. Cache status.json

Deploy: /opt/ecocupon/agent-local/
"""

import asyncio
import httpx
import json
import os
import subprocess
import time
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# ─── CONFIG ───────────────────────────────────────────────
BASE_DIR = Path("/opt/ecocupon/agent-local")
RECOVERY_RULES = BASE_DIR / "recovery_rules.json"
RECOVERY_LOG = BASE_DIR / "recovery_log.json"
STATUS_CACHE = BASE_DIR / "status_cache.json"

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rjfcmmzjlguiititkmyh.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
TELEGRAM_BOT = os.getenv("TELEGRAM_BOT_TOKEN", "7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6683244662")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))

# ─── SERVICES ─────────────────────────────────────────────
SERVICES = {
    "agent":        {"url": "http://127.0.0.1:9001/health",   "timeout": 3},
    "odoo":         {"url": "http://127.0.0.1:8070",          "timeout": 5},
    "qr":           {"url": "http://127.0.0.1:9004/health",   "timeout": 3},
    "bolt":         {"url": "http://127.0.0.1:8501/healthz",  "timeout": 5},
    "n8n":          {"url": "http://127.0.0.1:5678/healthz",  "timeout": 5},
    "caddy":        {"url": "http://127.0.0.1:2019/config/",  "timeout": 2},
    "postgres":     {"type": "tcp", "host": "127.0.0.1", "port": 5432, "timeout": 2},
    "redis":        {"type": "tcp", "host": "127.0.0.1", "port": 6379, "timeout": 2},
    "llm":          {"url": "http://127.0.0.1:8000/health",   "timeout": 5},
    "picoclaw":     {"url": "http://127.0.0.1:18792/health",  "timeout": 3},
}

# ─── STATE ────────────────────────────────────────────────
_cached_status = None
_last_check = None
_recovery_history = []
_shutdown = False

# ─── FASTAPI ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background loop on startup, stop on shutdown."""
    task = asyncio.create_task(background_loop())
    yield
    global _shutdown
    _shutdown = True
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="EcoCupon Agent Local", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "agent-local",
        "uptime": time.monotonic(),
        "last_check": _last_check,
        "cached": _cached_status is not None
    }


@app.get("/status.json")
@app.get("/status")
@app.get("/services")
async def get_status():
    if _cached_status:
        return _cached_status
    return {"status": "unknown", "services": {}, "message": "First check pending"}


@app.get("/recovery.json")
async def get_recovery():
    """Historial de auto-recovery actions."""
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
    """Check all services in parallel."""
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
    for name, result in results.items():
        if result["status"] == "down":
            overall = "degraded"
            break

    return {
        "status": overall,
        "services": results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0-unified"
    }


# ─── AUTO-RECOVERY ────────────────────────────────────────
def load_recovery_rules() -> dict:
    try:
        with open(RECOVERY_RULES) as f:
            return json.load(f)
    except Exception:
        return {"services": {}, "policy": {"max_retries": 3, "cooldown_after_success_sec": 300}}


def load_recovery_log() -> list:
    try:
        with open(RECOVERY_LOG) as f:
            data = json.load(f)
            return data if isinstance(data, list) else data.get("actions", [])
    except Exception:
        return []


def save_recovery_log():
    with open(RECOVERY_LOG, "w") as f:
        json.dump({"actions": _recovery_history[-100:]}, f, indent=2)


def should_attempt_recovery(service: str, rules: dict) -> bool:
    """Check cooldown and max retries."""
    policy = rules.get("policy", {})
    cooldown = policy.get("cooldown_after_success_sec", 300)
    max_retries = policy.get("max_retries", 3)

    # Count recent attempts
    recent = [a for a in _recovery_history
              if a["service"] == service
              and (datetime.now(timezone.utc) - datetime.fromisoformat(a["timestamp"])).total_seconds() < cooldown * 2]

    if len(recent) >= max_retries:
        return False

    # Check cooldown after success
    successes = [a for a in recent if a.get("result") == "success"]
    if successes:
        last_success = datetime.fromisoformat(successes[-1]["timestamp"])
        if (datetime.now(timezone.utc) - last_success).total_seconds() < cooldown:
            return False

    return True


async def attempt_recovery(service: str) -> dict:
    """Execute recovery action for a service."""
    rules = load_recovery_rules()
    svc_rules = rules.get("services", {}).get(service, {})

    if not svc_rules.get("auto_recover", False):
        return {"service": service, "result": "skipped", "reason": "auto_recover disabled"}

    if not should_attempt_recovery(service, rules):
        return {"service": service, "result": "skipped", "reason": "cooldown/max_retries"}

    cmd = svc_rules.get("restart_command", "")
    if not cmd:
        return {"service": service, "result": "failed", "reason": "no restart_command"}

    start = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        duration = int((time.monotonic() - start) * 1000)

        if proc.returncode == 0:
            # Verify service is actually running
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
            "return_code": proc.returncode
        }

        _recovery_history.append(action)
        save_recovery_log()
        return action

    except Exception as e:
        duration = int((time.monotonic() - start) * 1000)
        action = {
            "service": service,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": cmd,
            "result": "error",
            "error": str(e)[:200],
            "duration_ms": duration
        }
        _recovery_history.append(action)
        save_recovery_log()
        return action


# ─── TELEGRAM ALERTS ──────────────────────────────────────
async def send_telegram(message: str, parse_mode: str = "HTML"):
    """Send message to Telegram."""
    if not TELEGRAM_BOT or not TELEGRAM_CHAT:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT, "text": message, "parse_mode": parse_mode}
            )
    except Exception:
        pass


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
                    "Prefer": "return=minimal"
                },
                json={"service": service, "status": status, "latency_ms": latency, "details": details}
            )
    except Exception:
        pass


# ─── BACKGROUND LOOP ──────────────────────────────────────
async def background_loop():
    """Main monitoring loop: check → log → recover → alert."""
    global _cached_status, _last_check

    # Load recovery history
    _recovery_history[:] = load_recovery_log()

    while not _shutdown:
        try:
            # 1. Check all services
            status = await check_all_services()
            _cached_status = status
            _last_check = status["timestamp"]

            # 2. Log to Supabase + attempt recovery for down services
            for name, result in status["services"].items():
                await log_to_supabase(name, result["status"], result.get("latency_ms", 0), result)

                if result["status"] == "down":
                    # 3. Auto-recovery
                    recovery = await attempt_recovery(name)
                    if recovery["result"] in ("success", "partial"):
                        await send_telegram(
                            f"🔧 <b>AUTO-RECOVERY</b>\n"
                            f"✅ {name.upper()} recuperado\n"
                            f"⏱ {recovery.get('duration_ms', '?')}ms\n"
                            f"⏰ {datetime.now(timezone.utc).strftime('%H:%M')} UTC"
                        )
                    else:
                        await send_telegram(
                            f"🚨 <b>SERVICIO DOWN</b>\n"
                            f"❌ {name.upper()}: {result.get('error', 'sin respuesta')}\n"
                            f"🔧 Recovery: {recovery['result']}\n"
                            f"⏰ {datetime.now(timezone.utc).strftime('%H:%M')} UTC"
                        )

        except Exception as e:
            print(f"[ERROR] background_loop: {e}", flush=True)

        await asyncio.sleep(CHECK_INTERVAL)


# ─── ENTRY POINT ──────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print(f"🟡⚫ Agent Local v2.0 — {datetime.now(timezone.utc).isoformat()}", flush=True)
    print(f"   Services: {len(SERVICES)} | Interval: {CHECK_INTERVAL}s", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="warning")
