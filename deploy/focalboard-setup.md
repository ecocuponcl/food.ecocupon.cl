#!/usr/bin/env python3
"""
Focalboard Setup Instructions
══════════════════════════════
Run once via UI at https://flow.smarterbot.store

Step 1: Create Admin Account
- Open https://flow.smarterbot.store
- Username: admin
- Email: admin@smarterbot.cl  
- Password: SmarterOS2026!

Step 2: Create Board "Revenue Pipeline"
- Click "+ Add Board" → "Create a new board"
- Name: "Revenue Pipeline"
- Description: "SmarterOS lead → payment pipeline"

Step 3: Create 6 Columns (Status property)
Property name: "Status"
Type: Select
Options:
  1. 🔵 Lead Nuevo (propColorBlue)
  2. 🟡 Cotizado (propColorYellow)
  3. 🟠 Link Enviado (propColorOrange)
  4. ✅ Pagado (propColorGreen)
  5. 🟢 Activo (propColorPurple)
  6. ❌ Perdido (propColorGray)

Step 4: Create Card Properties
- Score (Number)
- Producto (Select: CLAWBOT, Hosting, Kiosk, Subscription, OpenClaw)
- Plan (Select: Starter Mensual, Starter Anual, Starter Bianual)
- Precio UF (Number)
- Precio CLP (Number)
- Accion (Select: Enviar cotizacion, Enviar link pago, Activar servicio, Cerrar agresivo)
- Pagado (Checkbox)
- Telegram Chat ID (Text)

Step 5: Create Test Card
- Title: "Test Lead - Carlos Méndez"
- Status: 🔵 Lead Nuevo
- Score: 95
- Producto: CLAWBOT
- Plan: Starter Anual
- Precio UF: 25
- Precio CLP: 950000
- Telegram Chat ID: 6683244662

Step 6: Configure Webhook (for n8n integration)
- Settings → Webhooks → Add Webhook
- URL: https://n8n.smarterbot.store/webhook/focalboard-card
- Events: card_created, card_updated
- Secret: smarteros-webhook-secret-2026
"""

print("Focalboard setup instructions saved.")
print("Open: https://flow.smarterbot.store")
print("Login: admin / SmarterOS2026!")
print("\nOnce board is created, the n8n workflow WF-PAY-04 will auto-process cards.")
