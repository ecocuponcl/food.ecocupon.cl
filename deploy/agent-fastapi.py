#!/usr/bin/env python3
"""
SmarterBOT FastAPI Agent
═════════════════════════
Monitors: lead-webhook (:8004), revenue-engine, qr-mobile (:9010), agent-bridge (:9011)
Auto-repairs: Restart services, clear cache
Reports: Daily to Volt + Telegram

Deploy: /opt/smarterbot/agent-fastapi.py
"""

import os
import json
import time
import httpx
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════
BASE = Path("/opt/smarterbot")
AGENT_LOG = BASE / "agent-fastapi-log.json"

SERVICES = {
    "lead-webhook": {"url": "http://127.0.0.1:8004/health", "service": "lead-webhook"},
    "agent-local": {"url": "http://127.0.0.1:8002/health", "service": "smarterbot-agent"},
    "bolt-balance": {"url": None, "service": "bolt-balance"},
    "revenue-engine": {"url": None, "service": "revenue-engine"},
    "qr-mobile": {"url": "http://127.0.0.1:9010/health", "service": "qr-mobile"},
    "agent-bridge": {"url": "http://127.0.0.1:9011/health", "service": "agent-bridge"},
    "hot-lead-alert": {"url": None, "service": "hot-lead-alert"},
    "auto-invoice": {"url": None, "service": "auto-invoice"}
}

VOLTURL = "http://127.0.0.1:9011"
TG_BOT = os.getenv("TELEGRAM_BOT_TOKEN", "7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6683244662")

CHECK_INTERVAL = 1800  # 30 minutes

# ═══════════════════════════════════════════════════════════
# CHECKS
# ═══════════════════════════════════════════════════════════
def check_service_health(name, config):
    """Check a single FastAPI service."""
    result = {"name": name}
    
    # Check systemd service
    try:
        r = subprocess.run(["systemctl", "is-active", config["service"]], 
                          capture_output=True, text=True, timeout=5)
        result["service_status"] = r.stdout.strip()
    except:
        result["service_status"] = "unknown"
    
    # Check HTTP health if available
    if config.get("url"):
        try:
            r = httpx.get(config["url"], timeout=5)
            result["http_status"] = r.status_code
            result["response_time_ms"] = round(r.elapsed.total_seconds() * 1000, 1)
        except Exception as e:
            result["http_status"] = 0
            result["http_error"] = str(e)[:100]
    
    result["healthy"] = result["service_status"] == "active"
    if config.get("url"):
        result["healthy"] = result["healthy"] and result.get("http_status", 0) == 200
    
    return result

def check_all_services():
    """Check all FastAPI services."""
    results = {}
    for name, config in SERVICES.items():
        results[name] = check_service_health(name, config)
    return results

def check_endpoint_latency():
    """Check latency of key endpoints."""
    endpoints = {
        "status": "http://127.0.0.1:8002/status.json",
        "balance": "http://127.0.0.1:8002/balance.json",
        "revenue": "http://127.0.0.1:8002/revenue.json",
        "tower": "http://127.0.0.1:8002/tower.html"
    }
    results = {}
    for name, url in endpoints.items():
        try:
            start = time.time()
            r = httpx.get(url, timeout=10, follow_redirects=True)
            latency = (time.time() - start) * 1000
            results[name] = {"status": r.status_code, "latency_ms": round(latency, 1)}
        except Exception as e:
            results[name] = {"status": 0, "error": str(e)[:100]}
    return results

# ═══════════════════════════════════════════════════════════
# AUTO-REPAIR
# ═══════════════════════════════════════════════════════════
def repair_service(name, config):
    """Restart a failed service."""
    service = config.get("service", name)
    try:
        subprocess.run(["systemctl", "restart", service], timeout=15)
        time.sleep(3)
        check = check_service_health(name, config)
        return {"status": "success" if check["healthy"] else "failed"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def restart_all():
    """Restart all FastAPI services."""
    results = {}
    for name, config in SERVICES.items():
        results[name] = repair_service(name, config)
    return results

# ═══════════════════════════════════════════════════════════
# REPORTING
# ═══════════════════════════════════════════════════════════
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

def report_to_volt(report):
    try:
        httpx.post(f"{VOLTURL}/api/agent/sync", json={
            "action": "daily_report",
            "agent": "fastapi",
            "report": report,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, timeout=10)
        return True
    except:
        return False

def save_log(entry):
    try:
        with open(AGENT_LOG) as f:
            logs = json.load(f)
    except:
        logs = {"checks": []}
    logs["checks"].insert(0, entry)
    logs["checks"] = logs["checks"][:100]
    with open(AGENT_LOG, "w") as f:
        json.dump(logs, f, indent=2, default=str)

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
def run_check():
    print(f"[{datetime.now(timezone.utc).isoformat()[:19]}] ⚡ FastAPI Agent check...", flush=True)
    
    report = {"agent": "fastapi", "timestamp": datetime.now(timezone.utc).isoformat()}
    
    # Check all services
    services = check_all_services()
    report["services"] = {k: {"healthy": v["healthy"], "service": v["service_status"]} 
                         for k, v in services.items()}
    
    # Check endpoint latency
    latency = check_endpoint_latency()
    report["latency"] = latency
    
    # Count healthy
    healthy = sum(1 for s in services.values() if s["healthy"])
    total = len(services)
    report["summary"] = {"healthy": healthy, "total": total}
    
    # Auto-repair failed services
    repairs = {}
    for name, check in services.items():
        if not check["healthy"]:
            print(f"  ⚠️ {name} unhealthy, repairing...", flush=True)
            repairs[name] = repair_service(name, SERVICES[name])
    
    if repairs:
        report["repairs"] = repairs
        services = check_all_services()
        report["services_after_repair"] = {k: {"healthy": v["healthy"]} for k, v in services.items()}
    
    save_log(report)
    report_to_volt(report)
    
    print(f"  Healthy: {healthy}/{total}, Repairs: {len(repairs)}", flush=True)
    return report

def main():
    print(f"⚡ SmarterBOT FastAPI Agent", flush=True)
    print(f"   Services: {len(SERVICES)}", flush=True)
    print(f"   Check interval: {CHECK_INTERVAL}s", flush=True)
    
    while True:
        try:
            run_check()
        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            save_log({"error": str(e), "ts": datetime.now(timezone.utc).isoformat()})
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
