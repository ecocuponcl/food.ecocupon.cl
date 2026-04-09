#!/usr/bin/env python3
"""
SmarterBOT Telegram Agent
══════════════════════════
Monitors: Bot uptime, message delivery, chat activity, error rate
Auto-repairs: Restart bot, resend failed messages
Reports: To Volt Bridge (port 9011)

Deploy: /opt/smarterbot/agent-telegram.py
"""

import os
import json
import time
import httpx
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/opt/smarterbot")
AGENT_LOG = BASE / "agent-telegram-log.json"
TG_BOT = os.getenv("TELEGRAM_BOT_TOKEN", "7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6683244662")
VOLT_URL = "http://127.0.0.1:9011"
CHECK_INTERVAL = 3600  # 1 hour

async def get_me():
    """Check bot status."""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"https://api.telegram.org/bot{TG_BOT}/getMe")
            if r.status_code == 200:
                data = r.json()
                return {"status": "ok", "name": data.get("result", {}).get("first_name", "?")}
            return {"status": "error", "code": r.status_code}
    except Exception as e:
        return {"status": "error", "error": str(e)[:100]}

async def send_test_message():
    """Test message delivery."""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(f"https://api.telegram.org/bot{TG_BOT}/sendMessage",
                json={"chat_id": TG_CHAT, "text": "🤖 Bot health check — OK"})
            return {"status": "ok" if r.status_code == 200 else "error", "code": r.status_code}
    except Exception as e:
        return {"status": "error", "error": str(e)[:100]}

async def get_updates():
    """Check for recent updates/messages."""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"https://api.telegram.org/bot{TG_BOT}/getUpdates?limit=5")
            if r.status_code == 200:
                data = r.json()
                updates = data.get("result", [])
                return {"status": "ok", "updates": len(updates)}
            return {"status": "error", "code": r.status_code}
    except Exception as e:
        return {"status": "error", "error": str(e)[:100]}

def check_bot_service():
    """Check if telegram bot service is running."""
    import subprocess
    services = ["smarter-telegram-bot"]
    status = {}
    for svc in services:
        try:
            r = subprocess.run(["systemctl", "is-active", svc], capture_output=True, text=True)
            status[svc] = r.stdout.strip()
        except:
            status[svc] = "unknown"
    return status

def report_to_volt(report):
    try:
        httpx.post(f"{VOLT_URL}/api/agent/sync", json={
            "action": "daily_report",
            "agent": "telegram",
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
    import asyncio
    print(f"[{datetime.now(timezone.utc).isoformat()[:19]}] 📱 Telegram Agent check...", flush=True)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    bot_status = loop.run_until_complete(get_me())
    delivery = loop.run_until_complete(send_test_message())
    updates = loop.run_until_complete(get_updates())
    
    loop.close()
    
    service_status = check_bot_service()
    
    report = {
        "agent": "telegram",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "bot": bot_status,
        "delivery": delivery,
        "updates": updates,
        "services": service_status
    }
    
    healthy = (
        bot_status.get("status") == "ok" and
        delivery.get("status") == "ok"
    )
    report["summary"] = {"healthy": healthy}
    
    # Auto-repair: restart bot service if down
    if not healthy or any(v != "active" for v in service_status.values()):
        print(f"  ⚠️ Bot issues detected, attempting repair...", flush=True)
        import subprocess
        try:
            subprocess.run(["systemctl", "restart", "smarter-telegram-bot"], timeout=15)
            report["repair"] = {"status": "restarted"}
        except Exception as e:
            report["repair"] = {"status": "error", "error": str(e)[:100]}
    
    save_log(report)
    report_to_volt(report)
    
    print(f"  Bot: {bot_status.get('status')}, Delivery: {delivery.get('status')}", flush=True)
    return report

def main():
    print(f"📱 SmarterBOT Telegram Agent", flush=True)
    print(f"   Bot: {TG_BOT[:10]}...", flush=True)
    print(f"   Check interval: {CHECK_INTERVAL}s (1h)", flush=True)
    
    while True:
        try:
            run_check()
        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            save_log({"error": str(e), "ts": datetime.now(timezone.utc).isoformat()})
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
