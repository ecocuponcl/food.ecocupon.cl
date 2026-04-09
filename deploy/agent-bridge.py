#!/usr/bin/env python3
"""
SmarterBOT External Agent Bridge
═══════════════════════════════════
API endpoints for external agent (Mac Mini/Orange Pi with Volt AGI)
- POST /api/agent/analyze → Send lead to external agent for analysis
- POST /api/agent/sync → Sync benchmarks and weights
- GET /api/agent/status → Check bridge status
- GET /api/agent/leads → Get leads for external processing

Deploy: Integrated into lead-webhook.py or standalone on :9011
"""

import os
import json
import httpx
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SmarterBOT Agent Bridge", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════
BASE = Path("/opt/smarterbot")
LEADS = BASE / "agent/leads.json"
WEIGHTS = BASE / "scoring-weights.json"
MEMORY_DB = BASE / "memory.db"

# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════
def load_leads():
    try:
        with open(LEADS) as f:
            data = json.load(f)
        return data.get("leads", []) if isinstance(data, dict) else data
    except:
        return []

def load_weights():
    try:
        with open(WEIGHTS) as f:
            return json.load(f)
    except:
        return {}

# ═══════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════
@app.get("/api/agent/status")
async def agent_status():
    """Check bridge status for external agent."""
    leads = load_leads()
    hot = [l for l in leads if l.get("revenue_score", 0) >= 85]
    warm = [l for l in leads if 40 <= l.get("revenue_score", 0) < 85]
    
    return {
        "status": "online",
        "bridge": "v1.0.0",
        "leads_total": len(leads),
        "hot_leads": len(hot),
        "warm_leads": len(warm),
        "weights": load_weights(),
        "memory_db": MEMORY_DB.exists(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/agent/leads")
async def get_leads(status: str = "all", limit: int = 20):
    """Get leads for external processing."""
    leads = load_leads()
    
    if status == "hot":
        leads = [l for l in leads if l.get("revenue_score", 0) >= 85]
    elif status == "warm":
        leads = [l for l in leads if 40 <= l.get("revenue_score", 0) < 85]
    elif status == "unprocessed":
        leads = [l for l in leads if not l.get("llm_replied")]
    
    return {
        "leads": leads[:limit],
        "total": len(leads),
        "limit": limit
    }

@app.post("/api/agent/analyze")
async def analyze_lead(request: Request):
    """Send lead to external agent for deep analysis."""
    data = await request.json()
    lead_id = data.get("lead_id")
    external_analysis = data.get("analysis")
    
    if not lead_id or not external_analysis:
        return {"status": "error", "message": "lead_id and analysis required"}
    
    # Update lead with external analysis
    leads_data = load_leads()
    leads = leads_data.get("leads", []) if isinstance(leads_data, dict) else leads_data
    
    for l in leads:
        if str(l.get("id")) == str(lead_id):
            l["external_analysis"] = external_analysis
            l["external_score"] = external_analysis.get("score", l.get("revenue_score"))
            l["analyzed_at"] = datetime.now(timezone.utc).isoformat()
            break
    
    if isinstance(leads_data, dict):
        leads_data["leads"] = leads
    else:
        leads_data = {"leads": leads, "total": len(leads)}
    
    with open(LEADS, "w") as f:
        json.dump(leads_data, f, indent=2, default=str)
    
    return {"status": "ok", "lead_id": lead_id}

@app.post("/api/agent/sync")
async def sync_benchmarks(request: Request):
    """Sync benchmarks and weights with external agent."""
    data = await request.json()
    action = data.get("action", "pull")
    
    if action == "pull":
        # External agent pulls current state
        return {
            "leads": load_leads()[:10],
            "weights": load_weights(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    elif action == "push":
        # External agent pushes updated weights
        new_weights = data.get("weights")
        if new_weights:
            with open(WEIGHTS, "w") as f:
                json.dump(new_weights, f, indent=2)
            return {"status": "ok", "message": "Weights updated"}
    
    return {"status": "error", "message": "Invalid action"}

@app.get("/api/agent/memory/{lead_id}")
async def get_lead_memory(lead_id: str):
    """Get lead memory profile."""
    try:
        import sqlite3
        conn = sqlite3.connect(str(MEMORY_DB))
        c = conn.cursor()
        c.execute("SELECT * FROM lead_profiles WHERE lead_id = ?", (lead_id,))
        row = c.fetchone()
        conn.close()
        
        if row:
            return {
                "lead_id": row[0],
                "name": row[1],
                "interactions": row[7],
                "first_seen": row[5],
                "last_seen": row[6]
            }
        return {"status": "not_found"}
    except:
        return {"status": "error"}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent-bridge"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9011, log_level="info")
