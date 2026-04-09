#!/usr/bin/env python3
"""
SmarterBOT Local Memory System
═══════════════════════════════
SQLite-based long-term memory for leads
Simple embeddings for similarity search
Lead conversation history tracking

Deploy: /opt/smarterbot/local-memory.py
Used by: lead-webhook.py, revenue-engine.py
"""

import os
import json
import sqlite3
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════
BASE = Path("/opt/smarterbot")
MEMORY_DB = BASE / "memory.db"

# ═══════════════════════════════════════════════════════════
# DATABASE INIT
# ═══════════════════════════════════════════════════════════
def init():
    conn = sqlite3.connect(str(MEMORY_DB))
    c = conn.cursor()
    
    # Lead profiles (long-term memory)
    c.execute('''CREATE TABLE IF NOT EXISTS lead_profiles (
        lead_id TEXT PRIMARY KEY,
        name TEXT,
        email TEXT,
        phone TEXT,
        product TEXT,
        first_seen TEXT,
        last_seen TEXT,
        interactions INTEGER DEFAULT 1,
        score_history TEXT,
        status_history TEXT,
        notes TEXT
    )''')
    
    # Conversation cache (similarity search)
    c.execute('''CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id TEXT,
        message TEXT,
        response TEXT,
        embedding_hash TEXT,
        ts TEXT
    )''')
    c.execute("CREATE INDEX IF NOT EXISTS idx_conv_lead ON conversations(lead_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_conv_hash ON conversations(embedding_hash)")
    
    # Pattern recognition
    c.execute('''CREATE TABLE IF NOT EXISTS patterns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pattern_type TEXT,
        pattern_data TEXT,
        confidence REAL,
        ts TEXT
    )''')
    
    conn.commit()
    return conn

# ═══════════════════════════════════════════════════════════
# SIMPLE EMBEDDINGS (Hash-based for speed)
# ═══════════════════════════════════════════════════════════
def simple_embedding(text):
    """Create simple hash-based embedding for similarity search."""
    # In production would use sentence-transformers
    # For now: character n-gram hash (fast, lightweight)
    text = text.lower()[:500]
    hashes = []
    for n in [2, 3, 4]:
        for i in range(len(text) - n + 1):
            h = hashlib.md5(text[i:i+n].encode()).hexdigest()[:8]
            hashes.append(h)
    return ",".join(sorted(set(hashes))[:50])

def find_similar_conversations(conn, message, threshold=0.3):
    """Find similar past conversations."""
    emb = simple_embedding(message)
    emb_set = set(emb.split(","))
    
    c = conn.cursor()
    c.execute("SELECT id, lead_id, message, response, embedding_hash FROM conversations ORDER BY id DESC LIMIT 100")
    
    similar = []
    for row in c.fetchall():
        row_emb = set(row[4].split(","))
        overlap = len(emb_set & row_emb) / max(len(emb_set | row_emb), 1)
        if overlap > threshold:
            similar.append({
                "id": row[0],
                "lead_id": row[1],
                "message": row[2],
                "response": row[3],
                "similarity": round(overlap, 3)
            })
    
    return sorted(similar, key=lambda x: x["similarity"], reverse=True)[:5]

# ═══════════════════════════════════════════════════════════
# LEAD PROFILE
# ═══════════════════════════════════════════════════════════
def update_profile(conn, lead):
    """Update or create lead profile."""
    c = conn.cursor()
    lead_id = str(lead.get("id", ""))
    
    # Check if exists
    c.execute("SELECT * FROM lead_profiles WHERE lead_id = ?", (lead_id,))
    existing = c.fetchone()
    
    now = datetime.now(timezone.utc).isoformat()
    
    if existing:
        # Update
        c.execute("""UPDATE lead_profiles SET 
            last_seen = ?, 
            interactions = interactions + 1,
            score_history = ?,
            status_history = ?,
            notes = ?
            WHERE lead_id = ?""",
            (now,
             json.dumps(lead.get("score_history", [])),
             json.dumps(lead.get("status_history", [])),
             lead.get("notes", ""),
             lead_id))
    else:
        # Create
        c.execute("""INSERT INTO lead_profiles 
            (lead_id, name, email, phone, product, first_seen, last_seen, interactions)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
            (lead_id,
             lead.get("name", ""),
             lead.get("email", ""),
             lead.get("phone", ""),
             lead.get("product", ""),
             now, now))
    
    conn.commit()

def get_lead_profile(conn, lead_id):
    """Get full lead profile."""
    c = conn.cursor()
    c.execute("SELECT * FROM lead_profiles WHERE lead_id = ?", (str(lead_id),))
    row = c.fetchone()
    if not row:
        return None
    
    return {
        "lead_id": row[0],
        "name": row[1],
        "email": row[2],
        "phone": row[3],
        "product": row[4],
        "first_seen": row[5],
        "last_seen": row[6],
        "interactions": row[7],
        "score_history": json.loads(row[8]) if row[8] else [],
        "status_history": json.loads(row[9]) if row[9] else [],
        "notes": row[10]
    }

# ═══════════════════════════════════════════════════════════
# CONVERSATION CACHE
# ═══════════════════════════════════════════════════════════
def add_conversation(conn, lead_id, message, response):
    """Add conversation to cache with embedding."""
    c = conn.cursor()
    emb = simple_embedding(message)
    c.execute("""INSERT INTO conversations (lead_id, message, response, embedding_hash, ts)
        VALUES (?, ?, ?, ?, ?)""",
        (str(lead_id), message[:500], response[:500], emb,
         datetime.now(timezone.utc).isoformat()))
    conn.commit()

def get_conversation_history(conn, lead_id, limit=10):
    """Get conversation history for a lead."""
    c = conn.cursor()
    c.execute("""SELECT message, response, ts FROM conversations 
        WHERE lead_id = ? ORDER BY ts DESC LIMIT ?""",
        (str(lead_id), limit))
    return [{"message": r[0], "response": r[1], "ts": r[2]} for r in c.fetchall()]

# ═══════════════════════════════════════════════════════════
# PATTERN RECOGNITION
# ═══════════════════════════════════════════════════════════
def detect_patterns(conn):
    """Detect patterns in lead data."""
    c = conn.cursor()
    
    # Pattern 1: Time-based conversion rate
    c.execute("""SELECT strftime('%H', ts) as hour, COUNT(*) as cnt,
        AVG(CASE WHEN status IN ('hot', 'mobile_engaged') THEN 1 ELSE 0 END) as conv_rate
        FROM conversations
        GROUP BY hour
        HAVING cnt >= 3
        ORDER BY conv_rate DESC""")
    
    patterns = []
    for row in c.fetchall():
        if row[2] > 0.5:
            patterns.append({
                "type": "high_conversion_hour",
                "data": {"hour": row[0], "rate": round(row[2], 3)},
                "confidence": min(row[1] / 10, 1.0)
            })
    
    # Save patterns
    for p in patterns:
        c.execute("""INSERT INTO patterns (pattern_type, pattern_data, confidence, ts)
            VALUES (?, ?, ?, ?)""",
            (p["type"], json.dumps(p["data"]), p["confidence"],
             datetime.now(timezone.utc).isoformat()))
    conn.commit()
    
    return patterns

# ═══════════════════════════════════════════════════════════
# API ENDPOINTS (for external agent bridge)
# ═══════════════════════════════════════════════════════════
def api_get_profile(lead_id):
    conn = init()
    profile = get_lead_profile(conn, lead_id)
    conn.close()
    return profile

def api_update_profile(lead):
    conn = init()
    update_profile(conn, lead)
    conn.close()
    return {"status": "ok"}

def api_find_similar(message):
    conn = init()
    similar = find_similar_conversations(conn, message)
    conn.close()
    return {"similar": similar}

def api_add_conversation(lead_id, message, response):
    conn = init()
    add_conversation(conn, lead_id, message, response)
    conn.close()
    return {"status": "ok"}

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
def main():
    print(f"🧠 SmarterBOT Local Memory System", flush=True)
    conn = init()
    
    # Detect patterns
    patterns = detect_patterns(conn)
    print(f"  Detected {len(patterns)} patterns", flush=True)
    for p in patterns[:3]:
        print(f"    {p['type']}: {p['data']} (confidence: {p['confidence']:.2f})", flush=True)
    
    # Stats
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM lead_profiles")
    profiles = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM conversations")
    conversations = c.fetchone()[0]
    
    print(f"  Profiles: {profiles}, Conversations: {conversations}", flush=True)
    conn.close()

if __name__ == "__main__":
    main()
