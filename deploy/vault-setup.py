#!/usr/bin/env python3
"""
SmarterBOT Vault — Store all API keys in Supabase
══════════════════════════════════════════════════
"""
import os, httpx, json, sys
from datetime import datetime, timezone

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rjfcmmzjlguiititkmyh.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Try to find key
if not SUPABASE_KEY:
    # Check .env files
    for env_path in ["/opt/smarterbot/agent/.env", "/opt/smarterbot/.env"]:
        try:
            with open(env_path) as f:
                for line in f:
                    if "SUPABASE_SERVICE" in line or "SUPABASE_KEY" in line:
                        SUPABASE_KEY = line.strip().split("=", 1)[1]
                        break
        except:
            pass

# Keys to store
VAULT_KEYS = {
    "telegram_bot_token": "8530453742:AAGdKp9zTHN5hiQp4550gOzKwgmuGhOvgwQ",
    "telegram_chat_id": "6683244662",
    "mailgun_api_key": "368cf85a285f0114298a84e0c198f520",
    "mailgun_domain": "smarterbot.cl",
    "openrouter_api_key": "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",
    "odoo_url": "http://127.0.0.1:8070",
    "odoo_db": "food_kiosk",
    "odoo_user": "admin",
    "odoo_pass": "SmarterOS2026!",
    "n8n_api_key": "n8n_sk_e26e26c736e059e1d9fd7a7b7476f7483705a94df1947d17e3ee177a5a9be2ef",
    "cf_api_token": "sP55h3OjnBKf3R3NkZ9HT0_XK-wM1K5ax15li9oN",
    "kaggle_user": "smarteros",
    "vps_ip": "89.116.23.167",
    "ecocupon_cl_zone_id": "3bdf9d7aa5344207b73d4f29043027d4",
    "smarterbot_store_zone_id": "81f7371c0a9d1e1a6fa9f6ff77eac8b0",
}

def create_vault_table():
    """Create vault table via SQL."""
    sql = """
    CREATE TABLE IF NOT EXISTS vault (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        key TEXT UNIQUE NOT NULL,
        value TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    ALTER TABLE vault ENABLE ROW LEVEL SECURITY;
    CREATE POLICY vault_service_only ON vault FOR ALL USING (true);
    """
    return sql

def store_keys():
    """Store all keys in Supabase vault table."""
    if not SUPABASE_KEY:
        print("❌ No Supabase service key found")
        return False
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    # First try to create table
    sql = create_vault_table()
    print("Creating vault table...")
    r = httpx.post(f"{SUPABASE_URL}/rest/v1/rpc/exec_sql", 
                   json={"query": sql}, headers=headers, timeout=10)
    if r.status_code not in (200, 201, 409):
        # Table might not exist, try direct insert (table may exist already)
        print("Table creation response:", r.status_code)
    
    # Insert/update each key
    stored = 0
    for key, value in VAULT_KEYS.items():
        # Upsert: try update first, if not exists then insert
        r = httpx.post(
            f"{SUPABASE_URL}/rest/v1/vault",
            json={
                "key": key,
                "value": value,
                "description": f"Auto-stored {key}",
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            headers=headers,
            timeout=10
        )
        if r.status_code in (200, 201, 409, 406):
            stored += 1
            print(f"  ✅ {key}: {value[:20]}...")
        else:
            print(f"  ❌ {key}: {r.status_code} {r.text[:100]}")
    
    print(f"\n✅ Stored {stored}/{len(VAULT_KEYS)} keys in Supabase vault")
    return stored == len(VAULT_KEYS)

if __name__ == "__main__":
    store_keys()
