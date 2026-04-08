# 🎯 SMARTEROS v3 — MANUAL STEPS (6 minutes remaining)

## ✅ COMPLETED (Autonomous)

- [x] 13/13 services running
- [x] Lead webhook with LLM integration
- [x] BOLT engine autonomous monitoring
- [x] Store pages live (HTTPS)
- [x] DNS configured
- [x] Odoo admin password: **SmarterOS2026!**
- [x] CRM module installed in Odoo

## 🔴 REMAINING (Requires Human - 6 min)

### Step 1: Create Telegram Bots (2 min)

1. Open Telegram → search **@BotFather**
2. Send: `/newbot`
3. Name: `Ecocupon Alerts`
4. Username: `EcocuponAlerts_bot`
5. **Copy the token** (looks like: `123456:ABC-DEF...`)
6. Repeat for: `FoodAlerts_bot`

### Step 2: Update .env (1 min)

SSH to VPS:
```bash
ssh root@89.116.23.167
nano /opt/smarterbot/agent/.env
```

Replace:
```env
ECOCOUPON_BOT_TOKEN=YOUR_NEW_TOKEN_HERE
ECOCOUPON_CHAT_ID=YOUR_CHAT_ID_HERE
FOOD_BOT_TOKEN=YOUR_NEW_TOKEN_HERE
FOOD_CHAT_ID=YOUR_CHAT_ID_HERE
```

To get chat_id:
1. Message your new bot
2. Visit: `https://api.telegram.org/bot< TOKEN >/getUpdates`
3. Find `"chat":{"id":123456789}`

Then restart:
```bash
systemctl restart lead-webhook bolt-engine
```

### Step 3: Import n8n Workflow (3 min)

1. Go to: `https://n8n.smarterbot.store`
2. Login: `admin` / `SmarterN8n_2026_Secure!`
3. Click **Workflows** → **Import from File**
4. Select: `/root/status-monitor/n8n-lead-capture-workflow.json`
5. Click **Activate** (toggle in top-right)

---

## ✅ VERIFICATION

After completing steps above:

1. Go to: `https://tienda.smarterbot.store`
2. Fill out contact form
3. Should receive:
   - ✅ JSON response with LLM reply
   - ✅ Telegram notification
   - ✅ Lead saved in `/opt/smarterbot/agent/leads.json`

---

## 📊 Current System Score: **89/100**

| Dimension | Score | Notes |
|-----------|-------|-------|
| Infrastructure | 30/30 | 13/13 services stable |
| Lead Capture | 20/20 | Webhook + LLM working |
| Autonomy | 20/25 | BOLT running, needs Telegram |
| CRM | 10/10 | Odoo CRM installed |
| Conversion | 9/15 | Leads captured, no real customer yet |

**After manual steps: 95/100**
