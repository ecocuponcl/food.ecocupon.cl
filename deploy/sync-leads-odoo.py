#!/usr/bin/env python3
"""
Sync leads.json → Odoo CRM
═══════════════════════════
Creates partners and CRM leads in Odoo from local leads.json
Maps:
  revenue_score → priority (0-3)
  product → expected_revenue
  status → stage_id
"""

import json
import xmlrpc.client
from datetime import datetime, timezone

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════
ODOO_URL = "http://127.0.0.1:8070"
ODOO_DB = "food_kiosk"
ODOO_USER = "admin"
ODOO_PASS = "SmarterOS2026!"

LEADS_FILE = "/opt/smarterbot/agent/leads.json"

# Product pricing (UF)
PRODUCT_UF = {
    "CLAWBOT": 25,
    "Hosting": 5,
    "Kiosk": 15,
    "Odoo": 30,
    "General": 10
}

UF_CLP = 38000  # 1 UF ≈ 38,000 CLP

# Score to Odoo priority (0-3)
def score_to_priority(score):
    if score >= 85: return "3"
    if score >= 70: return "2"
    if score >= 40: return "1"
    return "0"

# ═══════════════════════════════════════════════════════════
# ODOO CONNECTION
# ═══════════════════════════════════════════════════════════
common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})
print(f"Connected to Odoo: UID={uid}")

# ═══════════════════════════════════════════════════════════
# LOAD LEADS
# ═══════════════════════════════════════════════════════════
with open(LEADS_FILE) as f:
    data = json.load(f)
leads = data.get("leads", []) if isinstance(data, dict) else data
print(f"Loaded {len(leads)} leads from leads.json")

# ═══════════════════════════════════════════════════════════
# SYNC
# ═══════════════════════════════════════════════════════════
created = 0
updated = 0
skipped = 0
errors = 0

for lead in leads:
    nombre = lead.get("name", "").strip()
    email = lead.get("email", "").strip()
    phone = lead.get("phone", "").strip()
    message = lead.get("message", "").strip()
    product = lead.get("product", "General").strip()
    score = lead.get("revenue_score", 0)
    status = lead.get("status", "new")
    source = lead.get("source", "webhook")
    timestamp = lead.get("timestamp", "")
    lead_id = lead.get("id", "")
    
    if not nombre:
        skipped += 1
        continue
    
    try:
        # Check if partner exists by email
        partner_id = None
        if email:
            partners = models.execute_kw(ODOO_DB, uid, ODOO_PASS, "res.partner", "search", [[["email", "=", email]]])
            if partners:
                partner_id = partners[0]
        
        # Create partner if not exists
        if not partner_id:
            partner_vals = {"name": nombre}
            if email:
                partner_vals["email"] = email
            if phone:
                partner_vals["phone"] = phone
            
            partner_id = models.execute_kw(ODOO_DB, uid, ODOO_PASS, "res.partner", "create", [partner_vals])
        
        # Check if CRM lead already exists
        if email:
            existing = models.execute_kw(ODOO_DB, uid, ODOO_PASS, "crm.lead", "search", [[["email_from", "=", email]]])
            if existing:
                # Update existing
                priority = score_to_priority(score)
                uf_value = PRODUCT_UF.get(product, 10)
                expected_revenue = uf_value * UF_CLP
                
                models.execute_kw(ODOO_DB, uid, ODOO_PASS, "crm.lead", "write", [existing, {
                    "priority": priority,
                    "expected_revenue": expected_revenue,
                    "description": f"Score: {score}/100\nProduct: {product}\nSource: {source}\nTimestamp: {timestamp}\n\nMessage: {message}"
                }])
                updated += 1
                continue
        
        # Create new CRM lead
        priority = score_to_priority(score)
        uf_value = PRODUCT_UF.get(product, 10)
        expected_revenue = uf_value * UF_CLP
        
        crm_lead = models.execute_kw(ODOO_DB, uid, ODOO_PASS, "crm.lead", "create", [{
            "name": f"SmarterBOT: {nombre} — {product}",
            "partner_id": partner_id,
            "contact_name": nombre,
            "email_from": email,
            "phone": phone,
            "priority": priority,
            "expected_revenue": expected_revenue,
            "description": f"Score: {score}/100\nProduct: {product}\nSource: {source}\nTimestamp: {timestamp}\n\nMessage: {message}",
            "type": "opportunity",
            "tag_ids": [(6, 0, [])]  # Will add tags if they exist
        }])
        
        created += 1
        print(f"  ✅ {nombre}: score={score}, priority={priority}, revenue={expected_revenue:,} CLP ({uf_value} UF)")
        
    except Exception as e:
        errors += 1
        print(f"  ❌ {nombre}: {str(e)[:100]}")

print(f"\nSync complete:")
print(f"  Created: {created}")
print(f"  Updated: {updated}")
print(f"  Skipped: {skipped}")
print(f"  Errors:  {errors}")

# Verify
total_leads = models.execute_kw(ODOO_DB, uid, ODOO_PASS, "crm.lead", "search_count", [[],])
print(f"\nTotal CRM leads in Odoo: {total_leads}")
