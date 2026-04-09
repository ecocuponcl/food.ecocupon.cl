#!/usr/bin/env python3
"""
SmarterBOT Kaggle Agent
══════════════════════
Monitors: Dataset sync, notebook status, benchmark scores, CSV freshness
Auto-repairs: Re-sync CSVs, re-push notebook, fix export cron
Reports: To Volt Bridge (port 9011) + Telegram

Deploy: /opt/smarterbot/agent-kaggle.py
"""

import os
import json
import time
import httpx
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path("/opt/smarterbot")
AGENT_LOG = BASE / "agent-kaggle-log.json"
KAGGLE_DIR = BASE / "kaggle-dataset"
VOLT_URL = "http://127.0.0.1:9011"
TG_BOT = os.getenv("TELEGRAM_BOT_TOKEN", "7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6683244662")
CHECK_INTERVAL = 43200  # 12 hours

def check_dataset_freshness():
    """Check if Kaggle CSVs are fresh."""
    files = ["leads.csv", "balance.csv", "revenue_actions.csv"]
    status = {}
    now = datetime.now(timezone.utc)
    
    for f in files:
        path = KAGGLE_DIR / f
        if path.exists():
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            age_hours = (now - mtime).total_seconds() / 3600
            status[f] = {
                "exists": True,
                "age_hours": round(age_hours, 1),
                "fresh": age_hours < 6,
                "size_kb": round(path.stat().st_size / 1024, 1)
            }
        else:
            status[f] = {"exists": False, "fresh": False}
    
    return status

def check_kaggle_cli():
    """Check Kaggle CLI connectivity."""
    try:
        result = subprocess.run(
            ["kaggle", "datasets", "status", "-d", "smarteros/smarteros-leads"],
            capture_output=True, text=True, timeout=30
        )
        return {"status": "ok" if result.returncode == 0 else "error", "output": result.stdout[:200]}
    except Exception as e:
        return {"status": "error", "error": str(e)[:100]}

def check_notebook():
    """Check notebook status."""
    try:
        result = subprocess.run(
            ["kaggle", "kernels", "status", "smarteros/notebookb1a741d484"],
            capture_output=True, text=True, timeout=30
        )
        return {"status": "ok" if result.returncode == 0 else "error", "output": result.stdout.strip()}
    except Exception as e:
        return {"status": "error", "error": str(e)[:100]}

def check_benchmarks():
    """Check benchmark scores."""
    try:
        weights_path = BASE / "scoring-weights.json"
        if weights_path.exists():
            with open(weights_path) as f:
                weights = json.load(f)
            return {"status": "ok", "weights": weights}
        return {"status": "no_weights"}
    except:
        return {"status": "error"}

def check_cron():
    """Check if Kaggle export cron is active."""
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        cron_lines = result.stdout.split("\n")
        kaggle_cron = [l for l in cron_lines if "kaggle" in l.lower()]
        return {"status": "ok" if kaggle_cron else "missing", "crons": kaggle_cron}
    except:
        return {"status": "error"}

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
            "agent": "kaggle",
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

def run_check():
    print(f"[{datetime.now(timezone.utc).isoformat()[:19]}] 🏆 Kaggle Agent check...", flush=True)
    
    report = {"agent": "kaggle", "timestamp": datetime.now(timezone.utc).isoformat()}
    
    report["dataset"] = check_dataset_freshness()
    report["kaggle_cli"] = check_kaggle_cli()
    report["notebook"] = check_notebook()
    report["benchmarks"] = check_benchmarks()
    report["cron"] = check_cron()
    
    # Count fresh files
    dataset = report.get("dataset", {})
    fresh_count = sum(1 for v in dataset.values() if isinstance(v, dict) and v.get("fresh"))
    total_count = len(dataset)
    report["summary"] = {"fresh": fresh_count, "total": total_count}
    
    # Auto-repair: re-sync if stale
    if fresh_count < total_count:
        print(f"  ⚠️ {total_count - fresh_count} stale files, re-syncing...", flush=True)
        try:
            subprocess.run(
                ["python3", "/opt/smarterbot/kaggle-bridge.py"],
                capture_output=True, text=True, timeout=120
            )
            report["repair"] = {"status": "success"}
        except Exception as e:
            report["repair"] = {"status": "error", "error": str(e)[:100]}
    
    # Auto-repair: fix cron if missing
    if report["cron"].get("status") == "missing":
        print(f"  ⚠️ Kaggle cron missing, adding...", flush=True)
        try:
            subprocess.run(
                ["bash", "-c", "echo '0 */12 * * * cd /opt/smarterbot && python3 kaggle-benchmarks.py 2>/dev/null' | crontab -"],
                capture_output=True, text=True
            )
            report["cron_repair"] = {"status": "success"}
        except Exception as e:
            report["cron_repair"] = {"status": "error", "error": str(e)[:100]}
    
    save_log(report)
    report_to_volt(report)
    
    print(f"  Dataset: {fresh_count}/{total_count} fresh", flush=True)
    return report

def main():
    print(f"🏆 SmarterBOT Kaggle Agent", flush=True)
    print(f"   Dataset: {KAGGLE_DIR}", flush=True)
    print(f"   Check interval: {CHECK_INTERVAL}s (12h)", flush=True)
    
    while True:
        try:
            run_check()
        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            save_log({"error": str(e), "ts": datetime.now(timezone.utc).isoformat()})
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
