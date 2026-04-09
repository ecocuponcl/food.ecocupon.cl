#!/usr/bin/env python3
"""
SmarterBOT Docker Agent
═══════════════════════
Monitors: 21 containers, disk usage, RAM, network, container health
Auto-repairs: Restart crashed containers, prune images, clean logs
Reports: To Volt Bridge (port 9011)

Deploy: /opt/smarterbot/agent-docker.py
"""

import os
import json
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/opt/smarterbot")
AGENT_LOG = BASE / "agent-docker-log.json"
VOLT_URL = "http://127.0.0.1:9011"
CHECK_INTERVAL = 1800  # 30 minutes

def run_cmd(cmd, timeout=15):
    """Run shell command."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {"code": r.returncode, "stdout": r.stdout.strip(), "stderr": r.stderr.strip()[:200]}
    except Exception as e:
        return {"code": -1, "error": str(e)[:100]}

def check_containers():
    """Check all Docker containers."""
    result = run_cmd("docker ps -a --format '{{.Names}}|{{.Status}}|{{.State}}'")
    if result["code"] != 0:
        return {"error": result.get("error", result.get("stderr"))}
    
    containers = {}
    for line in result["stdout"].split("\n"):
        if "|" in line:
            parts = line.split("|")
            name = parts[0]
            status = parts[1]
            state = parts[2] if len(parts) > 2 else "?"
            running = "Up" in status
            containers[name] = {
                "status": status[:50],
                "state": state,
                "running": running
            }
    return containers

def check_disk_usage():
    """Check Docker disk usage."""
    result = run_cmd("docker system df --format '{{.Type}}: {{.Size}}'")
    if result["code"] != 0:
        return {"error": result.get("error", result.get("stderr"))}
    
    usage = {}
    for line in result["stdout"].split("\n"):
        if ": " in line:
            key, val = line.split(": ", 1)
            usage[key] = val
    return usage

def check_system_disk():
    """Check system disk usage."""
    result = run_cmd("df -h / | tail -1 | awk '{print $3 \" used / \" $2 \" total (\" $5 \")\"}'")
    return {"usage": result.get("stdout", "?")}

def check_ram():
    """Check RAM usage."""
    result = run_cmd("free -m | grep Mem | awk '{print \"used: \" $3 \"MB / \" $2 \"MB (\" int($3/$2*100) \"%)\"}'")
    return {"ram": result.get("stdout", "?")}

def count_restarts():
    """Count container restarts."""
    result = run_cmd("docker ps -a --format '{{.Names}}|{{.RestartCount}}'")
    if result["code"] != 0:
        return {}
    
    restarts = {}
    for line in result["stdout"].split("\n"):
        if "|" in line:
            name, count = line.split("|")
            if int(count) > 0:
                restarts[name] = int(count)
    return restarts

def prune_if_needed():
    """Auto-prune if disk usage high."""
    result = run_cmd("docker system df --format '{{.Type}}|{{.Size}}'")
    if result["code"] == 0:
        for line in result["stdout"].split("\n"):
            if "|" in line and "Images" in line:
                _, size = line.split("|", 1)
                # If images > 5GB, prune
                if "GB" in size:
                    gb = float(size.replace("GB", "").strip())
                    if gb > 5:
                        print(f"  ⚠️ Images at {gb}GB, pruning...", flush=True)
                        prune_result = run_cmd("docker system prune -f", timeout=30)
                        return {"pruned": True, "result": prune_result.get("stdout", "")[:200]}
    return {"pruned": False}

def report_to_volt(report):
    import httpx
    try:
        httpx.post(f"{VOLT_URL}/api/agent/sync", json={
            "action": "daily_report",
            "agent": "docker",
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
    print(f"[{datetime.now(timezone.utc).isoformat()[:19]}] 🐳 Docker Agent check...", flush=True)
    
    report = {"agent": "docker", "timestamp": datetime.now(timezone.utc).isoformat()}
    
    report["containers"] = check_containers()
    report["disk"] = check_disk_usage()
    report["system_disk"] = check_system_disk()
    report["ram"] = check_ram()
    report["restarts"] = count_restarts()
    
    # Count healthy containers
    containers = report.get("containers", {})
    if isinstance(containers, dict):
        running = sum(1 for v in containers.values() if isinstance(v, dict) and v.get("running"))
        total = len(containers)
        report["summary"] = {"running": running, "total": total}
        
        # Auto-repair: restart crashed containers
        for name, info in containers.items():
            if isinstance(info, dict) and not info.get("running") and info.get("state") != "exited":
                print(f"  ⚠️ Container {name} not running, restarting...", flush=True)
                run_cmd(f"docker restart {name}", timeout=30)
                report.setdefault("repairs", {})[name] = "restarted"
    
    # Auto-prune if needed
    prune_result = prune_if_needed()
    if prune_result.get("pruned"):
        report["prune"] = prune_result
    
    save_log(report)
    report_to_volt(report)
    
    summary = report.get("summary", {})
    print(f"  Containers: {summary.get('running', 0)}/{summary.get('total', 0)} running", flush=True)
    return report

def main():
    print(f"🐳 SmarterBOT Docker Agent", flush=True)
    print(f"   Check interval: {CHECK_INTERVAL}s (30m)", flush=True)
    
    while True:
        try:
            run_check()
        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            save_log({"error": str(e), "ts": datetime.now(timezone.utc).isoformat()})
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
