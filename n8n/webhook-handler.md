# n8n Webhook Handler — EcoCupon Agent

## Webhook URL
```
POST https://n8n.smarterbot.cl/webhook/ecocupon-agent
```

## Input (from Agent /decide)
```json
{
  "vertical": "RECYCLE | VEHICLE | KIOSK",
  "intent": "EVALUATE | ACTION | SUPPORT",
  "scoring": {
    "confidence": 0.9,
    "value_clp": 500,
    "reasoning": "PET 500ml detectado"
  },
  "decision": "approve | reject | review | comprar | negociar | descartar",
  "options": [
    {"action": "cashback", "amount": 500, "label": "+$500 CLP a wallet"}
  ],
  "metadata": {
    "event_id": "uuid",
    "user_phone": "56912345678",
    "lat": -33.45,
    "lng": -70.66
  },
  "next_step": "n8n_triggered",
  "event_id": "uuid"
}
```

## Workflow Routes

### 1. RECYCLE + approve
```
n8n → Supabase: INSERT recycle_events
    → Supabase: UPDATE wallets SET balance = balance + reward
    → Telegram: "♻️ +$500 CLP por reciclar PET"
    → Odoo: Log transaction
```

### 2. RECYCLE + review
```
n8n → Supabase: INSERT recycle_events (status=pending)
    → Telegram admin: "⚠️ Reciclaje pendiente de revisión"
    → Wait for admin action
```

### 3. RECYCLE + reject
```
n8n → Supabase: INSERT recycle_events (status=rejected)
    → Telegram: "❌ Reciclaje rechazado: {reason}"
```

### 4. VEHICLE + comprar
```
n8n → Odoo CRM: Create lead (hot)
    → WhatsApp: "🚗 Vehículo a buen precio — ¿quieres agendar visita?"
    → Supabase: INSERT vehicle_evaluations
```

### 5. VEHICLE + negociar
```
n8n → WhatsApp: "💡 Precio sugerido: ${suggested} — ¿enviar oferta?"
    → Supabase: INSERT vehicle_evaluations
```

### 6. VEHICLE + descartar
```
n8n → WhatsApp: "⚠️ Sobreprecio detectado — alternativa reciclaje: $X"
    → Supabase: INSERT vehicle_evaluations
    → If user interested in recycle → trigger recycle flow
```

### 7. KIOSK + qr_generated
```
n8n → Odoo: Attach QR tokens to order
    → Print: Send QR to kiosk printer
    → Telegram: "🎉 Cashback potencial: $X CLP si reciclas"
```
