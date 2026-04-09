#!/usr/bin/env python3
"""
Volt Reporter — Consolidates all agent reports and sends daily summary
═══════════════════════════════════════════════════════════════════════
Receives reports from: Odoo, n8n, FastAPI, Supabase agents
Consolidates and sends daily summary to Telegram
Also acts as the central coordination hub

Deploy: /opt/smarterbot/volt-reporter.py
Trigger: Daily at 18:00 (cron)
"""

import os
import json
import httpx
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════
BASE = Path("/opt/smarterbot")
DAILY_REPORT = BASE / "daily-reports"
DAILY_REPORT.mkdir(exist_ok=True)

VOLT_URL = "http://127.0.0.1:9011"
TG_BOT = os.getenv("TELEGRAM_BOT_TOKEN", "7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6683244662")

AGENTS = ["odoo", "n8n", "fastapi", "supabase"]

# ═══════════════════════════════════════════════════════════
# COLLECT REPORTS
# ═══════════════════════════════════════════════════════════
def collect_agent_reports():
    """Collect latest reports from all agents."""
    reports = {}
    
    for agent in AGENTS:
        log_file = BASE / f"agent-{agent}-log.json"
        try:
            with open(log_file) as f:
                data = json.load(f)
            latest = data.get("checks", [{}])[0] if data.get("checks") else {}
            reports[agent] = {
                "status": latest.get("health", {}).get("status", "unknown"),
                "last_check": latest.get("timestamp", "never"),
                "details": latest
            }
        except Exception as e:
            reports[agent] = {"status": "no_report", "error": str(e)}
    
    return reports

def get_current_system_state():
    """Get current state from Volt bridge."""
    try:
        r = httpx.get(f"{VOLT_URL}/api/agent/status", timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return {}

def get_revenue_summary():
    """Get revenue pipeline summary."""
    try:
        with open(BASE / "agent/leads.json") as f:
            data = json.load(f)
        leads = data.get("leads", []) if isinstance(data, dict) else data
        scored = [l for l in leads if l.get("revenue_score")]
        hot = [l for l in scored if l.get("revenue_score", 0) >= 85]
        warm = [l for l in scored if 40 <= l.get("revenue_score", 0) < 85]
        lost = [l for l in scored if l.get("revenue_action") == "mark_lost"]
        
        return {
            "total_leads": len(leads),
            "scored": len(scored),
            "hot": len(hot),
            "warm": len(warm),
            "lost": len(lost),
            "top_leads": [{"name": l.get("name"), "score": l.get("revenue_score")} for l in hot[:3]]
        }
    except:
        return {}

# ═══════════════════════════════════════════════════════════
# DAILY REPORT
# ═══════════════════════════════════════════════════════════
async def send_telegram(msg):
    if not TG_BOT or not TG_CHAT:
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            await c.post(f"https://api.telegram.org/bot{TG_BOT}/sendMessage",
                json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"})
        return True
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def generate_daily_report():
    """Generate consolidated daily report."""
    agent_reports = collect_agent_reports()
    system = get_current_system_state()
    revenue = get_revenue_summary()
    
    # Count healthy agents
    healthy = sum(1 for r in agent_reports.values() if r.get("status") in ["healthy", "ok"])
    
    # Save report
    report = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agents": agent_reports,
        "agents_healthy": healthy,
        "agents_total": len(AGENTS),
        "system": system,
        "revenue": revenue
    }
    
    report_file = DAILY_REPORT / f"report-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    return report

async def send_daily_report(report):
    """Send formatted daily report to Telegram."""
    agents = report.get("agents", {})
    revenue = report.get("revenue", {})
    date = report.get("date", "Unknown")
    
    # Agent status lines
    agent_lines = []
    for agent, info in agents.items():
        status = info.get("status", "?")
        icon = "✅" if status in ["healthy", "ok"] else "⚠️" if status == "degraded" else "❌"
        agent_lines.append(f"  {icon} {agent}: {status}")
    
    agents_healthy = report.get("agents_healthy", 0)
    agents_total = report.get("agents_total", 0)
    
    msg = (
        f"🤖 <b>Volt Daily Report — {date}</b>\n\n"
        f"📡 <b>Agents:</b> {agents_healthy}/{agents_total} healthy\n"
        + "\n".join(agent_lines) + "\n\n"
        f"💰 <b>Revenue Pipeline:</b>\n"
        f"  Leads: {revenue.get('total_leads', 0)}\n"
        f"  Scored: {revenue.get('scored', 0)}\n"
        f"  🔥 HOT: {revenue.get('hot', 0)}\n"
        f"  ⏳ Warm: {revenue.get('warm', 0)}\n"
        f"  ❌ Lost: {revenue.get('lost', 0)}\n"
    )
    
    # Add top leads
    top = revenue.get("top_leads", [])
    if top:
        msg += "\n🔥 <b>Top HOT Leads:</b>\n"
        for l in top:
            msg += f"  • {l.get('name', '?')}: {l.get('score', 0)}\n"
    
    msg += f"\n📊 Score: {min(100, 80 + agents_healthy * 4)}"
    
    return await send_telegram(msg)

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
def main():
    print(f"🤖 Volt Reporter — Daily Report Generator", flush=True)
    
    report = generate_daily_report()
    print(f"  Report generated for {report.get('date')}", flush=True)
    print(f"  Agents: {report.get('agents_healthy')}/{report.get('agents_total')} healthy", flush=True)
    
    asyncio.get_event_loop().run_until_complete(send_daily_report(report))
    print(f"  Report sent to Telegram", flush=True)

if __name__ == "__main__":
    main()
