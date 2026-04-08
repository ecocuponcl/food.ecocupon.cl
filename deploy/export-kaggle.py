#!/usr/bin/env python3
"""
Export leads.json → Kaggle-ready CSV
Run: python3 export-kaggle.py
Output: /opt/smarterbot/kaggle-dataset/data.csv
"""

import json
import csv
from pathlib import Path
from datetime import datetime

LEADS = Path("/opt/smarterbot/agent/leads.json")
OUTPUT = Path("/opt/smarterbot/kaggle-dataset/data.csv")

def export():
    try:
        with open(LEADS) as f:
            data = json.load(f)
    except:
        print("No leads found")
        return

    leads = data.get("leads", [])
    if not leads:
        print("No leads to export")
        return

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "timestamp", "id", "name", "email", "phone",
            "product", "message", "source", "llm_replied", "llm_at"
        ])
        writer.writeheader()
        for lead in leads:
            writer.writerow({
                "timestamp": lead.get("timestamp", ""),
                "id": lead.get("id", ""),
                "name": lead.get("name", ""),
                "email": lead.get("email", ""),
                "phone": lead.get("phone", ""),
                "product": lead.get("product", ""),
                "message": lead.get("message", "")[:200],
                "source": lead.get("source", ""),
                "llm_replied": "1" if lead.get("llm_replied") else "0",
                "llm_at": lead.get("llm_at", ""),
            })

    print(f"Exported {len(leads)} leads to {OUTPUT}")

if __name__ == "__main__":
    export()
