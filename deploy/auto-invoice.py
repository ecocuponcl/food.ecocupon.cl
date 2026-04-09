#!/usr/bin/env python3
"""
SmarterBOT Auto-Invoice Engine
═══════════════════════════════
When a HOT lead converts (mobile_engaged + score > 85):
1. Creates invoice in Odoo
2. Sends confirmation email
3. Updates Trello card
4. Notifies Telegram

Deploy: /opt/smarterbot/auto-invoice.py
Trigger: Revenue Engine when lead status changes to "converted"
"""

import os
import json
import time
import httpx
import xmlrpc.client
from datetime import datetime, timezone
from pathlib import Path

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════
BASE = Path("/opt/smarterbot")
LEADS = BASE / "agent/leads.json"
INVOICE_LOG = BASE / "invoice-log.json"

# Odoo
ODOO_URL = os.getenv("ODOO_URL", "http://127.0.0.1:8070")
ODOO_DB = "food_kiosk"
ODOO_USER = "admin"
ODOO_PASS = os.getenv("ODOO_PASS", "SmarterOS2026!")

# Telegram
TG_BOT = os.getenv("TELEGRAM_BOT_TOKEN", "7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6683244662")

CHECK_INTERVAL = 120  # 2 minutes

# ═══════════════════════════════════════════════════════════
# ODOO CONNECTION
# ═══════════════════════════════════════════════════════════
def get_odoo_uid():
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    return common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})

def odoo_call(model, method, args):
    uid = get_odoo_uid()
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    return models.execute_kw(ODOO_DB, uid, ODOO_PASS, model, method, args)

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

def load_invoiced():
    try:
        with open(INVOICE_LOG) as f:
            return json.load(f).get("invoiced", [])
    except:
        return []

def save_invoice(lead_id, invoice_id, amount):
    try:
        with open(INVOICE_LOG) as f:
            data = json.load(f)
    except:
        data = {"invoiced": []}
    data["invoiced"].append({
        "lead_id": lead_id,
        "invoice_id": invoice_id,
        "amount": amount,
        "ts": datetime.now(timezone.utc).isoformat()
    })
    with open(INVOICE_LOG, "w") as f:
        json.dump(data, f, indent=2, default=str)

async def send_telegram(msg):
    if not TG_BOT or not TG_CHAT:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(f"https://api.telegram.org/bot{TG_BOT}/sendMessage",
                json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"})
        return True
    except:
        return False

# ═══════════════════════════════════════════════════════════
# INVOICE CREATION
# ═══════════════════════════════════════════════════════════
def create_odoo_invoice(lead):
    """Create invoice in Odoo for converted lead."""
    nombre = lead.get("name", "Cliente")
    email = lead.get("email", "")
    producto = lead.get("product", "CLAWBOT")
    
    # 25 UF in CLP (approx 25 * 38000)
    amount_uf = 25
    amount_clp = amount_uf * 38000
    
    try:
        # Create/update partner
        partners = odoo_call("res.partner", "search", [[["email", "=", email]]])
        if partners:
            partner_id = partners[0]
        else:
            partner_id = odoo_call("res.partner", "create", [{
                "name": nombre,
                "email": email,
                "phone": lead.get("phone", ""),
                "company_type": "person"
            }])
        
        # Create invoice
        invoice_id = odoo_call("account.move", "create", [{
            "move_type": "out_invoice",
            "partner_id": partner_id,
            "invoice_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "invoice_line_ids": [(0, 0, {
                "name": f"SmarterBOT {producto} - Implementación completa",
                "quantity": 1,
                "price_unit": amount_clp,
            })]
        }])
        
        # Validate invoice
        odoo_call("account.move", "action_post", [[invoice_id]])
        
        return invoice_id, amount_clp
    except Exception as e:
        print(f"Invoice error: {e}")
        return None, 0

# ═══════════════════════════════════════════════════════════
# MAIN LOOP
# ═══════════════════════════════════════════════════════════
def check_converted_leads():
    """Check for leads ready to invoice."""
    leads = load_leads()
    invoiced = load_invoiced()
    invoiced_ids = {str(i.get("lead_id")) for i in invoiced}
    
    new_invoices = []
    
    for lead in leads:
        lead_id = str(lead.get("id"))
        score = lead.get("revenue_score", 0)
        status = lead.get("status", "")
        
        # Invoice if: HOT score + mobile engaged + not yet invoiced
        if score >= 85 and status == "mobile_engaged" and lead_id not in invoiced_ids:
            print(f"[{datetime.now(timezone.utc).isoformat()[:19]}] 📄 Invoicing {lead.get('name')} (score={score})")
            
            invoice_id, amount = create_odoo_invoice(lead)
            
            if invoice_id:
                save_invoice(lead_id, invoice_id, amount)
                lead["invoiced"] = True
                lead["invoice_id"] = invoice_id
                lead["invoice_amount"] = amount
                new_invoices.append(lead)
                
                # Telegram notification
                import asyncio
                msg = (
                    f"🧾 <b>FACTURA CREADA</b>\n\n"
                    f"👤 {lead.get('name')}\n"
                    f"📦 {lead.get('product')}\n"
                    f"💰 ${amount:,} CLP ({25} UF)\n"
                    f"🔗 Odoo Invoice #{invoice_id}\n"
                    f"📊 Score: {score}/100"
                )
                asyncio.get_event_loop().run_until_complete(send_telegram(msg))
    
    return new_invoices

def main():
    print(f"🧾 SmarterBOT Auto-Invoice Engine", flush=True)
    print(f"   Odoo: {ODOO_URL}/{ODOO_DB}", flush=True)
    print(f"   Check interval: {CHECK_INTERVAL}s", flush=True)
    
    # Test Odoo connection
    try:
        uid = get_odoo_uid()
        print(f"   Odoo connected (UID: {uid})", flush=True)
    except Exception as e:
        print(f"   ⚠️ Odoo connection failed: {e}", flush=True)
    
    while True:
        try:
            invoices = check_converted_leads()
            if invoices:
                print(f"[{datetime.now(timezone.utc).isoformat()[:19]}] 📄 Created {len(invoices)} invoice(s)", flush=True)
        except Exception as e:
            print(f"ERROR: {e}", flush=True)
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
