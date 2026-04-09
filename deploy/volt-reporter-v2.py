#!/usr/bin/env python3
"""
Volt Reporter v2 — Consolidates ALL 8 agent reports
══════════════════════════════════════════════════════
Receives reports from: Odoo, n8n, FastAPI, Supabase, Kaggle, Telegram, Caddy, Docker
Consolidates and sends daily summary to Telegram

Deploy: /opt/smarterbot/volt-reporter.py
Cron: Daily at 18:00
"""

import os
import json
import httpx
import asyncio
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/opt/smarterbot")
DAILY_REPORT = BASE / "daily-reports"
DAILY_REPORT.mkdir(exist_ok=True)

VOLT_URL = "http://127.0.0.1:9011"
TG_BOT = os.getenv("TELEGRAM_BOT_TOKEN", "7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6683244662")

AGENTS = {
    "odoo": "🏢 Odoo ERP",
    "n8n": "⚡ n8n Automation",
    "fastapi": "🌐 FastAPI Services",
    "supabase": "🗃️ Supabase DB",
    "kaggle": "🏆 Kaggle Benchmarks",
    "telegram": "📱 Telegram Bot",
    "caddy": "🔒 Caddy/SSL",
    "docker": "🐳 Docker"
}

def collect_agent_reports():
    """Collect latest reports from all 8 agents."""
    reports = {}
    for agent, label in AGENTS.items():
        log_file = BASE / f"agent-{agent}-log.json"
        try:
            with open(log_file) as f:
                data = json.load(f)
            latest = data.get("checks", [{}])[0] if data.get("checks") else {}
            reports[agent] = {
                "label": label,
                "status": latest.get("health", {}).get("status", latest.get("summary", {}).get("healthy", "unknown")),
                "last_check": latest.get("timestamp", "never"),
                "details": latest
            }
        except Exception as e:
            reports[agent] = {"label": label, "status": "no_report", "error": str(e)[:80]}
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

def get_docker_summary():
    """Get Docker container summary."""
    try:
        report = AGENTS.get("docker", {})
        details = report.get("details", {})
        summary = details.get("summary", {})
        return {
            "running": summary.get("running", 0),
            "total": summary.get("total", 0)
        }
    except:
        return {"running": 0, "total": 0}

def generate_daily_report():
    """Generate consolidated daily report."""
    agent_reports = collect_agent_reports()
    system = get_current_system_state()
    revenue = get_revenue_summary()
    docker = get_docker_summary()
    
    # Count healthy agents
    def is_healthy(r):
        s = r.get("status")
        return s in ["healthy", "ok", True] or (isinstance(s, int) and s > 70)
    
    healthy = sum(1 for r in agent_reports.values() if is_healthy(r))
    
    report = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agents": agent_reports,
        "agents_healthy": healthy,
        "agents_total": len(AGENTS),
        "system": system,
        "revenue": revenue,
        "docker": docker
    }
    
    report_file = DAILY_REPORT / f"report-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    return report

async def send_daily_report(report):
    """Send formatted daily report to Telegram."""
    agents = report.get("agents", {})
    revenue = report.get("revenue", {})
    docker = report.get("docker", {})
    date = report.get("date", "Unknown")
    
    agents_healthy = report.get("agents_healthy", 0)
    agents_total = report.get("agents_total", 0)
    
    # Agent status lines with emojis
    agent_lines = []
    for agent_key, info in AGENTS.items():
        agent_data = agents.get(agent_key, {})
        status = agent_data.get("status", "?")
        
        if status in ["healthy", "ok", True] or (isinstance(status, int) and status > 70):
            icon = "✅"
        elif status == "degraded":
            icon = "⚠️"
        else:
            icon = "❌"
        
        agent_lines.append(f"  {icon} {info}")
    
    top = revenue.get("top_leads", [])
    top_leads_text = ""
    if top:
        top_leads_text = "\n🔥 <b>Top HOT Leads:</b>\n"
        for l in top:
            top_leads_text += f"  • {l.get('name', '?')}: {l.get('score', 0)}\n"
    
    msg = (
        f"🤖 <b>Volt Daily Report — {date}</b>\n\n"
        f"📡 <b>Agents:</b> {agents_healthy}/{agents_total} healthy\n"
        + "\n".join(agent_lines) + f"\n\n"
        f"🐳 <b>Docker:</b> {docker.get('running', 0)}/{docker.get('total', 0)} containers\n\n"
        f"💰 <b>Revenue Pipeline:</b>\n"
        f"  Leads: {revenue.get('total_leads', 0)}\n"
        f"  Scored: {revenue.get('scored', 0)}\n"
        f"  🔥 HOT: {revenue.get('hot', 0)}\n"
        f"  ⏳ Warm: {revenue.get('warm', 0)}\n"
        f"  ❌ Lost: {revenue.get('lost', 0)}"
        + top_leads_text +
        f"\n📊 Score: {min(100, 70 + agents_healthy * 3 + docker.get('running', 0))}"
    )
    
    # Send via Telegram
    if not TG_BOT or not TG_CHAT:
        print("  Telegram not configured")
        return False
    
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            await c.post(f"https://api.telegram.org/bot{TG_BOT}/sendMessage",
                json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"})
        print(f"  Report sent to Telegram")
        return True
    except Exception as e:
        print(f"  Telegram error: {e}")
        return False

def main():
    print(f"🤖 Volt Reporter v2 — Daily Report Generator", flush=True)
    print(f"  Agents: {len(AGENTS)}", flush=True)
    
    report = generate_daily_report()
    print(f"  Report generated for {report.get('date')}", flush=True)
    print(f"  Agents: {report.get('agents_healthy')}/{report.get('agents_total')} healthy", flush=True)
    
    asyncio.get_event_loop().run_until_complete(send_daily_report(report))

if __name__ == "__main__":
    main()
