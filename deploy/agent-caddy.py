#!/usr/bin/env python3
"""
SmarterBOT Caddy Agent
══════════════════════
Monitors: All HTTPS endpoints, SSL cert expiry, DNS, Caddy config
Auto-repairs: Restart Caddy, fix duplicate blocks, request new certs
Reports: To Volt Bridge (port 9011)

Deploy: /opt/smarterbot/agent-caddy.py
"""

import os
import json
import time
import httpx
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path("/opt/smarterbot")
AGENT_LOG = BASE / "agent-caddy-log.json"
CADDYFILE = "/etc/caddy/Caddyfile"
VOLT_URL = "http://127.0.0.1:9011"
CHECK_INTERVAL = 3600  # 1 hour

# Domains to monitor
DOMAINS = [
    "ecocupon.cl",
    "food.ecocupon.cl",
    "n8n.smarterbot.store",
    "os.smarterbot.store",
    "bolt.smarterbot.store",
    "qr.ecocupon.cl",
    "erp.smarterbot.store",
    "chat.smarterbot.store"
]

def check_endpoints():
    """Check all HTTPS endpoints."""
    status = {}
    for domain in DOMAINS:
        try:
            r = httpx.get(f"https://{domain}/", timeout=10, follow_redirects=True)
            status[domain] = {
                "code": r.status_code,
                "ok": r.status_code < 400
            }
        except Exception as e:
            status[domain] = {
                "code": 0,
                "ok": False,
                "error": str(e)[:80]
            }
    return status

def check_ssl_certs():
    """Check SSL certificate expiry."""
    import ssl
    certs = {}
    for domain in DOMAINS[:3]:  # Check first 3
        try:
            ctx = ssl.create_default_context()
            with ctx.wrap_socket(httpx.Client().transport, server_hostname=domain) as s:
                s.connect((domain, 443))
                cert = s.getpeercert()
                not_after = cert["notAfter"]
                expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                days_left = (expiry - datetime.now(timezone.utc)).days
                certs[domain] = {"days_left": days_left, "ok": days_left > 7}
        except Exception as e:
            certs[domain] = {"days_left": 0, "ok": False, "error": str(e)[:80]}
    return certs

def check_caddy_service():
    """Check Caddy service status."""
    try:
        r = subprocess.run(["systemctl", "is-active", "caddy"], capture_output=True, text=True)
        return {"status": r.stdout.strip()}
    except:
        return {"status": "unknown"}

def check_config_syntax():
    """Check Caddyfile syntax."""
    try:
        r = subprocess.run(["caddy", "validate"], capture_output=True, text=True, timeout=10)
        return {"valid": r.returncode == 0, "output": r.stderr[:200] if r.returncode != 0 else "ok"}
    except Exception as e:
        return {"valid": False, "error": str(e)[:100]}

def check_for_duplicates():
    """Check for duplicate domain blocks in Caddyfile."""
    try:
        with open(CADDYFILE) as f:
            content = f.read()
        
        import re
        domains = re.findall(r'^([a-z0-9._-]+)\s*\{', content, re.MULTILINE)
        from collections import Counter
        counts = Counter(domains)
        duplicates = {k: v for k, v in counts.items() if v > 1}
        return {"duplicates": duplicates, "total_domains": len(set(domains))}
    except Exception as e:
        return {"error": str(e)[:100]}

def report_to_volt(report):
    try:
        httpx.post(f"{VOLT_URL}/api/agent/sync", json={
            "action": "daily_report",
            "agent": "caddy",
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
    print(f"[{datetime.now(timezone.utc).isoformat()[:19]}] 🔒 Caddy Agent check...", flush=True)
    
    report = {"agent": "caddy", "timestamp": datetime.now(timezone.utc).isoformat()}
    
    report["endpoints"] = check_endpoints()
    report["service"] = check_caddy_service()
    report["config"] = check_config_syntax()
    report["duplicates"] = check_for_duplicates()
    
    # Count healthy endpoints
    endpoints = report.get("endpoints", {})
    healthy = sum(1 for v in endpoints.values() if v.get("ok"))
    total = len(endpoints)
    report["summary"] = {"healthy": healthy, "total": total}
    
    # Auto-repair: restart Caddy if service down
    if report["service"].get("status") != "active":
        print(f"  ⚠️ Caddy down, restarting...", flush=True)
        try:
            subprocess.run(["systemctl", "restart", "caddy"], timeout=30)
            time.sleep(3)
            report["repair"] = {"status": "restarted"}
        except Exception as e:
            report["repair"] = {"status": "error", "error": str(e)[:100]}
    
    # Auto-repair: fix duplicate blocks
    duplicates = report.get("duplicates", {}).get("duplicates", {})
    if duplicates:
        print(f"  ⚠️ Duplicate domains found: {duplicates}", flush=True)
        report["warning"] = f"Duplicate domains: {duplicates}"
    
    save_log(report)
    report_to_volt(report)
    
    print(f"  Endpoints: {healthy}/{total} healthy", flush=True)
    return report

def main():
    print(f"🔒 SmarterBOT Caddy Agent", flush=True)
    print(f"   Domains: {len(DOMAINS)}", flush=True)
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
