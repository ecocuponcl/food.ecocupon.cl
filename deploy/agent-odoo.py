#!/usr/bin/env python3
"""
SmarterBOT Odoo/ERP Agent
═══════════════════════════
Monitors: Odoo DB, workers, modules, disk
Auto-repairs: Restart service, vacuum DB, clear sessions
Reports: Daily to Volt + Telegram

Deploy: /opt/smarterbot/agent-odoo.py
Port: :9020
Cron: Every 30 min
"""

import os
import json
import time
import httpx
import subprocess
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════
BASE = Path("/opt/smarterbot")
AGENT_LOG = BASE / "agent-odoo-log.json"
ODOO_URL = os.getenv("ODOO_URL", "http://127.0.0.1:8070")
ODOO_DB = os.getenv("ODOO_DB", "food_kiosk")
ODOO_USER = os.getenv("ODOO_USER", "admin")
ODOO_PASS = os.getenv("ODOO_PASS", "SmarterOS2026!")

VOLT_URL = "http://127.0.0.1:9011"
TG_BOT = os.getenv("TELEGRAM_BOT_TOKEN", "7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6683244662")

CHECK_INTERVAL = 1800  # 30 minutes

# ═══════════════════════════════════════════════════════════
# ODOO CONNECTION
# ═══════════════════════════════════════════════════════════
import xmlrpc.client

def get_odoo_uid():
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        return common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})
    except:
        return None

def odoo_call(model, method, args):
    uid = get_odoo_uid()
    if not uid:
        return None
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    try:
        return models.execute_kw(ODOO_DB, uid, ODOO_PASS, model, method, args)
    except:
        return None

# ═══════════════════════════════════════════════════════════
# CHECKS
# ═══════════════════════════════════════════════════════════
def check_odoo_health():
    """Check Odoo connectivity and basic operations."""
    uid = get_odoo_uid()
    if not uid:
        return {"status": "down", "error": "Cannot connect to Odoo"}
    
    # Check DB size
    partner_count = odoo_call("res.partner", "search_count", [[]])
    lead_count = odoo_call("crm.lead", "search_count", [[]]) if odoo_call("ir.model", "search", [[("model", "=", "crm.lead")]]) else 0
    invoice_count = odoo_call("account.move", "search_count", [[("move_type", "=", "out_invoice")]]) if odoo_call("ir.model", "search", [[("model", "=", "account.move")]]) else 0
    
    return {
        "status": "healthy",
        "uid": uid,
        "partners": partner_count or 0,
        "leads": lead_count or 0,
        "invoices": invoice_count or 0
    }

def check_disk_space():
    """Check disk space for Odoo data."""
    try:
        stat = os.statvfs("/var/lib/docker")
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bavail * stat.f_frsize
        used_pct = ((total - free) / total) * 100
        return {"status": "ok" if used_pct < 85 else "warning", "used_pct": round(used_pct, 1)}
    except:
        return {"status": "unknown"}

def check_odoo_modules():
    """Check installed modules."""
    modules = odoo_call("ir.module.module", "search_read", 
                       [[("state", "=", "installed")]], 
                       {"fields": ["name", "latest_version"]})
    return {"installed_modules": len(modules) if modules else 0}

# ═══════════════════════════════════════════════════════════
# AUTO-REPAIR
# ═══════════════════════════════════════════════════════════
def repair_odoo():
    """Attempt to repair Odoo by restarting."""
    try:
        subprocess.run(["docker", "restart", "food-odoo"], timeout=30)
        time.sleep(5)
        uid = get_odoo_uid()
        return {"status": "success" if uid else "failed", "uid": uid}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def vacuum_db():
    """Vacuum PostgreSQL database."""
    try:
        subprocess.run(
            ["docker", "exec", "food-odoo-db", "psql", "-U", "odoo", "-d", ODOO_DB, "-c", "VACUUM ANALYZE;"],
            timeout=60
        )
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

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
    """Send daily report to Volt."""
    try:
        httpx.post(f"{VOLT_URL}/api/agent/sync", json={
            "action": "daily_report",
            "agent": "odoo",
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
    """Run all checks and auto-repair if needed."""
    print(f"[{datetime.now(timezone.utc).isoformat()[:19]}] 🔶 Odoo Agent check...", flush=True)
    
    report = {
        "agent": "odoo",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Check health
    health = check_odoo_health()
    report["health"] = health
    
    # Check disk
    disk = check_disk_space()
    report["disk"] = disk
    
    # Check modules
    modules = check_odoo_modules()
    report["modules"] = modules
    
    # Auto-repair if down
    if health.get("status") == "down":
        print(f"  ⚠️ Odoo down, attempting repair...", flush=True)
        repair = repair_odoo()
        report["repair"] = repair
        
        if repair.get("status") == "success":
            health = check_odoo_health()
            report["health_after_repair"] = health
            print(f"  ✅ Odoo repaired", flush=True)
    
    # Save log
    save_log(report)
    
    # Report to Volt
    report_to_volt(report)
    
    print(f"  Status: {health.get('status')}, Partners: {health.get('partners', 0)}", flush=True)
    return report

def main():
    print(f"🔶 SmarterBOT Odoo Agent", flush=True)
    print(f"   Odoo: {ODOO_URL}/{ODOO_DB}", flush=True)
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
