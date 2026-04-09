#!/usr/bin/env python3
"""
SmarterBOT n8n Agent
═════════════════════
Monitors: n8n service, workflows, executions, DB size
Auto-repairs: Restart n8n, clean old executions
Reports: Daily to Volt + Telegram

Deploy: /opt/smarterbot/agent-n8n.py
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
AGENT_LOG = BASE / "agent-n8n-log.json"
N8N_URL = os.getenv("N8N_URL", "http://127.0.0.1:5678")
N8N_API = os.getenv("N8N_API", "")  # n8n API key

VOLT_URL = "http://127.0.0.1:9011"
TG_BOT = os.getenv("TELEGRAM_BOT_TOKEN", "7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6683244662")

CHECK_INTERVAL = 1800  # 30 minutes

# ═══════════════════════════════════════════════════════════
# CHECKS
# ═══════════════════════════════════════════════════════════
def check_n8n_health():
    """Check n8n service health."""
    try:
        r = httpx.get(f"{N8N_URL}/healthz", timeout=5)
        if r.status_code == 200:
            return {"status": "healthy", "response_time_ms": r.elapsed.total_seconds() * 1000}
        return {"status": "degraded", "code": r.status_code}
    except Exception as e:
        return {"status": "down", "error": str(e)}

def check_n8n_workflows():
    """Count active workflows."""
    try:
        r = httpx.get(f"{N8N_URL}/rest/workflows", timeout=10)
        if r.status_code == 200:
            workflows = r.json().get("data", [])
            active = sum(1 for w in workflows if w.get("active"))
            return {"total": len(workflows), "active": active}
    except:
        pass
    return {"total": 0, "active": 0}

def check_n8n_db_size():
    """Check n8n SQLite DB size."""
    try:
        db_path = "/var/lib/docker/volumes/n8n_data/_data/database.sqlite"
        if os.path.exists(db_path):
            size_mb = os.path.getsize(db_path) / (1024 * 1024)
            return {"size_mb": round(size_mb, 1), "status": "ok" if size_mb < 500 else "warning"}
    except:
        pass
    return {"size_mb": 0, "status": "unknown"}

def check_executions():
    """Check recent execution count and errors."""
    try:
        r = httpx.get(f"{N8N_URL}/rest/executions?take=100", timeout=10)
        if r.status_code == 200:
            execs = r.json().get("data", [])
            errors = sum(1 for e in execs if e.get("status") == "error")
            return {"total": len(execs), "errors": errors, "error_rate": round(errors/max(len(execs),1)*100, 1)}
    except:
        pass
    return {"total": 0, "errors": 0, "error_rate": 0}

# ═══════════════════════════════════════════════════════════
# AUTO-REPAIR
# ═══════════════════════════════════════════════════════════
def repair_n8n():
    """Restart n8n service."""
    try:
        subprocess.run(["docker", "restart", "smarter-n8n"], timeout=30)
        time.sleep(5)
        health = check_n8n_health()
        return {"status": "success" if health.get("status") == "healthy" else "failed"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def clean_old_executions():
    """Clean old executions to reduce DB size."""
    try:
        subprocess.run(
            ["docker", "exec", "smarter-n8n", "n8n", "execution:clear", "--yes"],
            timeout=60
        )
        return {"status": "success"}
    except:
        return {"status": "error"}

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
        httpx.post(f"{VOLT_URL}/api/agent/sync", json={
            "action": "daily_report",
            "agent": "n8n",
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
    print(f"[{datetime.now(timezone.utc).isoformat()[:19]}] 🔷 n8n Agent check...", flush=True)
    
    report = {"agent": "n8n", "timestamp": datetime.now(timezone.utc).isoformat()}
    
    # Check health
    health = check_n8n_health()
    report["health"] = health
    
    # Check workflows
    workflows = check_n8n_workflows()
    report["workflows"] = workflows
    
    # Check DB size
    db = check_n8n_db_size()
    report["db"] = db
    
    # Check executions
    execs = check_executions()
    report["executions"] = execs
    
    # Auto-repair if down
    if health.get("status") == "down":
        print(f"  ⚠️ n8n down, restarting...", flush=True)
        repair = repair_n8n()
        report["repair"] = repair
        health = check_n8n_health()
        report["health_after_repair"] = health
    
    # Clean DB if too large
    if db.get("size_mb", 0) > 500:
        print(f"  ⚠️ n8n DB too large ({db['size_mb']}MB), cleaning...", flush=True)
        clean = clean_old_executions()
        report["db_cleanup"] = clean
    
    save_log(report)
    report_to_volt(report)
    
    print(f"  Status: {health.get('status')}, Workflows: {workflows.get('active', 0)}/{workflows.get('total', 0)}", flush=True)
    return report

def main():
    print(f"🔷 SmarterBOT n8n Agent", flush=True)
    print(f"   n8n: {N8N_URL}", flush=True)
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
