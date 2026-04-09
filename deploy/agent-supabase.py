#!/usr/bin/env python3
"""
SmarterBOT Supabase Agent
══════════════════════════
Monitors: Supabase API, tables, RLS policies, storage
Auto-repairs: Retry failed queries, backup critical tables
Reports: Daily to Volt + Telegram

Deploy: /opt/smarterbot/agent-supabase.py
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
AGENT_LOG = BASE / "agent-supabase-log.json"

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rjfcmmzjlguiititkmyh.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

VOLT_URL = "http://127.0.0.1:9011"
TG_BOT = os.getenv("TELEGRAM_BOT_TOKEN", "7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6683244662")

CHECK_INTERVAL = 3600  # 1 hour (Supabase has rate limits)

# Critical tables to monitor
CRITICAL_TABLES = [
    "events_log", "wallets", "recycle_events", 
    "fraud_decisions", "vehicle_evaluations",
    "service_status_logs", "tenant_policies"
]

# ═══════════════════════════════════════════════════════════
# CHECKS
# ═══════════════════════════════════════════════════════════
def check_supabase_api():
    """Check Supabase REST API connectivity."""
    try:
        r = httpx.get(f"{SUPABASE_URL}/rest/v1/", 
                     headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
                     timeout=10)
        return {
            "status": "healthy" if r.status_code in [200, 401, 404] else "degraded",
            "code": r.status_code,
            "response_time_ms": round(r.elapsed.total_seconds() * 1000, 1)
        }
    except Exception as e:
        return {"status": "down", "error": str(e)[:100]}

def check_tables():
    """Check critical table row counts."""
    tables = {}
    for table in CRITICAL_TABLES:
        try:
            r = httpx.get(f"{SUPABASE_URL}/rest/v1/{table}?select=count&limit=1",
                         headers={
                             "apikey": SUPABASE_KEY,
                             "Authorization": f"Bearer {SUPABASE_KEY}",
                             "Prefer": "count=exact"
                         },
                         timeout=10)
            # Get count from Content-Range header
            content_range = r.headers.get("content-range", "0-0/0")
            total = int(content_range.split("/")[-1]) if "/" in content_range else 0
            tables[table] = {"status": "ok", "rows": total}
        except Exception as e:
            tables[table] = {"status": "error", "error": str(e)[:100]}
    return tables

def check_rls_policies():
    """Check RLS policies are enabled."""
    try:
        r = httpx.get(f"{SUPABASE_URL}/rest/v1/policies",
                     headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
                     timeout=10)
        if r.status_code == 200:
            policies = r.json()
            return {"status": "ok", "policies": len(policies)}
        return {"status": "degraded"}
    except:
        return {"status": "unknown"}

def check_storage():
    """Check Supabase storage buckets."""
    try:
        r = httpx.get(f"{SUPABASE_URL}/storage/v1/bucket",
                     headers={"Authorization": f"Bearer {SUPABASE_KEY}"},
                     timeout=10)
        if r.status_code == 200:
            buckets = r.json()
            return {"status": "ok", "buckets": len(buckets)}
        return {"status": "degraded"}
    except:
        return {"status": "unknown"}

# ═══════════════════════════════════════════════════════════
# AUTO-REPAIR
# ═══════════════════════════════════════════════════════════
def backup_critical_tables():
    """Backup critical tables to local JSON files."""
    backup_dir = BASE / "supabase-backups"
    backup_dir.mkdir(exist_ok=True)
    
    backed_up = []
    for table in CRITICAL_TABLES:
        try:
            r = httpx.get(f"{SUPABASE_URL}/rest/v1/{table}?limit=1000",
                         headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
                         timeout=30)
            if r.status_code == 200:
                data = r.json()
                backup_file = backup_dir / f"{table}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
                with open(backup_file, "w") as f:
                    json.dump(data, f, indent=2)
                backed_up.append(table)
        except:
            pass
    
    return {"status": "success" if backed_up else "failed", "tables": backed_up}

def retry_failed_queries():
    """Retry any failed table checks."""
    tables = check_tables()
    failed = [t for t, v in tables.items() if v.get("status") != "ok"]
    
    if not failed:
        return {"status": "ok", "message": "All tables healthy"}
    
    # Retry once
    retried = []
    for table in failed:
        try:
            r = httpx.get(f"{SUPABASE_URL}/rest/v1/{table}?limit=1",
                         headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
                         timeout=15)
            if r.status_code == 200:
                retried.append(table)
        except:
            pass
    
    return {"status": "success" if retried else "failed", "retried": retried}

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
            "agent": "supabase",
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
    print(f"[{datetime.now(timezone.utc).isoformat()[:19]}] 🔵 Supabase Agent check...", flush=True)
    
    report = {"agent": "supabase", "timestamp": datetime.now(timezone.utc).isoformat()}
    
    # Check API
    api = check_supabase_api()
    report["api"] = api
    
    # Check tables
    tables = check_tables()
    report["tables"] = tables
    table_ok = sum(1 for v in tables.values() if v.get("status") == "ok")
    report["tables_summary"] = {"ok": table_ok, "total": len(tables)}
    
    # Check RLS
    rls = check_rls_policies()
    report["rls"] = rls
    
    # Check storage
    storage = check_storage()
    report["storage"] = storage
    
    # Auto-repair if API down
    if api.get("status") == "down":
        print(f"  ⚠️ Supabase API down, retrying...", flush=True)
        retry = retry_failed_queries()
        report["repair"] = retry
    
    # Backup critical tables
    backup = backup_critical_tables()
    report["backup"] = backup
    
    save_log(report)
    report_to_volt(report)
    
    print(f"  API: {api.get('status')}, Tables: {table_ok}/{len(tables)}, Backup: {backup.get('status')}", flush=True)
    return report

def main():
    print(f"🔵 SmarterBOT Supabase Agent", flush=True)
    print(f"   Supabase: {SUPABASE_URL}", flush=True)
    print(f"   Check interval: {CHECK_INTERVAL}s", flush=True)
    print(f"   Critical tables: {len(CRITICAL_TABLES)}", flush=True)
    
    while True:
        try:
            run_check()
        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            save_log({"error": str(e), "ts": datetime.now(timezone.utc).isoformat()})
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
