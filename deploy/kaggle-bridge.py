#!/usr/bin/env python3
"""
Kaggle Bridge — Connects SmarterOS to Kaggle
══════════════════════════════════════════════
Exports leads to Kaggle dataset
Imports predictions back to Revenue Engine
Updates notebook with real production data

Deploy: /opt/smarterbot/kaggle-bridge.py
Run: cron every 5 min or on-demand
"""

import os
import json
import csv
import time
import httpx
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════
BASE = Path("/opt/smarterbot")
LEADS = BASE / "agent/leads.json"
KAGGLE_DIR = BASE / "kaggle-dataset"
KAGGLE_CRED = Path("/root/.kaggle/kaggle.json")

KAGGLE_NOTEBOOK_URL = os.getenv("KAGGLE_NOTEBOOK_URL", "https://www.kaggle.com/code/smarteros/notebookb1a741d484")
KAGGLE_USERNAME = os.getenv("KAGGLE_USERNAME", "smarteros")

# ═══════════════════════════════════════════════════════════
# EXPORT: Leads → Kaggle CSV
# ═══════════════════════════════════════════════════════════
def export_leads():
    """Export leads.json to Kaggle-ready CSV."""
    KAGGLE_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(LEADS) as f:
            data = json.load(f)
        leads = data.get("leads", []) if isinstance(data, dict) else data
    except:
        leads = []
    
    if not leads:
        print("[kaggle] No leads to export")
        return False
    
    # Main leads CSV
    csv_path = KAGGLE_DIR / "leads.csv"
    fieldnames = ["id", "timestamp", "name", "email", "phone", "product", "message", 
                  "source", "llm_replied", "revenue_score", "revenue_action", "status"]
    
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for lead in leads:
            row = {k: lead.get(k, "") for k in fieldnames}
            row["llm_replied"] = 1 if lead.get("llm_replied") else 0
            writer.writerow(row)
    
    # Balance snapshot CSV
    balance_path = KAGGLE_DIR / "balance.csv"
    try:
        with open(BASE / "status-balance.json") as f:
            balance = json.load(f)
        with open(balance_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["metric", "value"])
            writer.writeheader()
            writer.writerow({"metric": "balance_score", "value": balance.get("balance_score", 0)})
            writer.writerow({"metric": "yin_score", "value": balance.get("yin_score", 0)})
            writer.writerow({"metric": "yang_score", "value": balance.get("yang_score", 0)})
            writer.writerow({"metric": "flow_score", "value": balance.get("flow_score", 0)})
            writer.writerow({"metric": "stress_score", "value": balance.get("stress_score", 0)})
            writer.writerow({"metric": "leads_total", "value": balance.get("leads_total", 0)})
            writer.writerow({"metric": "error_rate", "value": balance.get("error_rate", 0)})
            writer.writerow({"metric": "timestamp", "value": balance.get("timestamp", "")})
    except Exception as e:
        print(f"[kaggle] Balance export error: {e}")
    
    # Revenue log CSV
    rev_path = KAGGLE_DIR / "revenue_actions.csv"
    try:
        with open(BASE / "revenue-log.json") as f:
            rev_data = json.load(f)
        actions = rev_data.get("actions", [])
        with open(rev_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["ts", "action", "detail", "status"])
            writer.writeheader()
            for a in actions[:100]:
                writer.writerow(a)
    except Exception as e:
        print(f"[kaggle] Revenue export error: {e}")
    
    print(f"[kaggle] Exported {len(leads)} leads to {csv_path}")
    return True

# ═══════════════════════════════════════════════════════════
# IMPORT: Kaggle predictions → Revenue Engine
# ═══════════════════════════════════════════════════════════
def import_predictions():
    """Import predictions from Kaggle notebook output."""
    # This would read predictions.json from the Kaggle dataset
    # For now, it's a placeholder for the bridge
    predictions_path = KAGGLE_DIR / "predictions.json"
    if not predictions_path.exists():
        return False
    
    try:
        with open(predictions_path) as f:
            preds = json.load(f)
        print(f"[kaggle] Imported {len(preds)} predictions")
        return True
    except:
        return False

# ═══════════════════════════════════════════════════════════
# KAGGLE NOTEBOOK SYNC
# ═══════════════════════════════════════════════════════════
def push_to_kaggle():
    """Push dataset to Kaggle (requires kaggle CLI)."""
    try:
        result = subprocess.run(
            ["kaggle", "datasets", "version", "-p", str(KAGGLE_DIR), 
             "-m", f"Auto-update {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            print(f"[kaggle] Dataset pushed: {result.stdout.strip()}")
            return True
        else:
            print(f"[kaggle] Push failed: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"[kaggle] Push error: {e}")
        return False

# ═══════════════════════════════════════════════════════════
# KAGGLE NOTEBOOK EXECUTION
# ═══════════════════════════════════════════════════════════
def trigger_notebook():
    """Trigger Kaggle notebook execution via API."""
    # This would use the Kaggle API to run the notebook
    # For now, it logs the intent
    print(f"[kaggle] Notebook: {KAGGLE_NOTEBOOK_URL}")
    print(f"[kaggle] To run: kaggle kernels push -p /path/to/notebook")
    return True

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
def main():
    print(f"🔗 Kaggle Bridge — SmarterOS ↔ Kaggle", flush=True)
    print(f"   Notebook: {KAGGLE_NOTEBOOK_URL}", flush=True)
    
    # Export leads to CSV
    if export_leads():
        # Push to Kaggle
        push_to_kaggle()
        # Import predictions back
        import_predictions()
        # Trigger notebook
        trigger_notebook()

if __name__ == "__main__":
    main()
