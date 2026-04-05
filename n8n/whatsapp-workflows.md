# n8n WhatsApp Workflows — EcoCupon (v2 con error handling)

## Config previa

### WhatsApp API
- **Opción A:** Meta Cloud API (oficial, gratis hasta 1000 conversaciones/mes)
- **Opción B:** Twilio WhatsApp (pago por mensaje)
- **Opción C:** WPPConnect (self-hosted, gratis)

### Variables de entorno en n8n
```
WHATSAPP_API_URL=https://graph.facebook.com/v17.0/TU_PHONE_ID/messages
WHATSAPP_TOKEN=EAAB...
WHATSAPP_TEMPLATE_NAME=ecocupon_notification
SUPABASE_URL=https://rjfcmmzjlguiititkmyh.supabase.co
SUPABASE_KEY=your_service_role_key
```

---

## ⚠️ Error Handling (TODOS los workflows)

Cada workflow DEBE tener:
1. **Idempotency Check**: Query Supabase `events_log` por `event_id` antes de procesar
2. **Retry Node**: 3 intentos con backoff exponencial antes de cada HTTP Request
3. **Error Branch**: Si falla → Telegram alert al admin
4. **Catch All**: Error trigger → log en Supabase

---

## Workflow 1: Reciclaje → WhatsApp

### Trigger
```
Webhook: POST /webhook/ecocupon-agent
Body: { vertical: "RECYCLE", decision: "approve", scoring: { value_clp: 50 }, metadata: { event_id: "uuid", user_phone: "56912345678" } }
```

### Nodes
```
1. Webhook → recibe evento
2. Supabase → SELECT id FROM events_log WHERE payload->>'event_id' = {{$json.metadata.event_id}}
3. IF → exists? → YES → Stop (duplicate)
4. IF → NO → Continue
5. Switch → filtra vertical = "RECYCLE"
6. IF → decision = "approve"
   ├─ YES → 7. HTTP Request (Retry 3x) → Supabase: INSERT recycle_events
   │         → 8. HTTP Request (Retry 3x) → Supabase: UPDATE wallets
   │         → 9. HTTP Request (Retry 3x) → WhatsApp API
   │         → 10. HTTP Request → Odoo: Log transaction
   │
   └─ NO → 11. IF → decision = "reject"
             ├─ YES → WhatsApp: "❌ Reciclaje rechazado: {{$json.scoring.reasoning}}"
             └─ NO → WhatsApp: "⚠️ Tu reciclaje está en revisión"

Error branch → Telegram admin: "❌ Error workflow reciclaje: {{$json.error}}"
```

### Template WhatsApp (Meta)
```
Nombre: ecocupon_recycle
Idioma: es
Cuerpo: "♻️ +${{1}} CLP por reciclar\n{{2}}\n\nSaldo actual: consulta en ecocupon.cl"
```

---

## Workflow 2: Vehículo → WhatsApp

### Nodes
```
1. Webhook → recibe evento
2. Supabase → Idempotency check
3. Switch → filtra vertical = "VEHICLE"
4. Switch → decision:
   ├─ "comprar" → WhatsApp: "🚗 {{marca}} {{modelo}} {{ano}} a buen precio (${{value_clp}}). ¿Agendar visita?"
   ├─ "negociar" → WhatsApp: "💡 {{marca}} {{modelo}} → Valor real: ${{value_clp}}. Precio sugerido: ${{suggested}}. ¿Enviar oferta?"
   └─ "descartar" → WhatsApp: "⚠️ {{marca}} {{modelo}} sobreprecio. Alternativa reciclaje: ${{recycle_value}}"

Error branch → Telegram admin
```

---

## Workflow 3: Kiosk → WhatsApp

### Nodes
```
1. Webhook → recibe evento
2. Supabase → Idempotency check
3. Switch → filtra vertical = "KIOSK"
4. HTTP Request (Retry 3x) → WhatsApp API
   Body: {
     "messaging_product": "whatsapp",
     "to": "{{ $json.metadata.user_phone }}",
     "type": "template",
     "template": {
       "name": "ecocupon_kiosk",
       "language": { "code": "es" },
       "components": [{
         "type": "body",
         "parameters": [
           { "type": "text", "text": "{{ $json.total_cashback }}" },
           { "type": "text", "text": "{{ $json.qr_tokens.length }}" }
         ]
       }]
     }
   }
```

---

## Workflow 4: Lead → Odoo CRM (FIX: sin duplicados)

### Nodes
```
1. Webhook → recibe evento (cualquier vertical con metadata.user_phone)
2. Supabase → SELECT id FROM wallets WHERE phone = {{$json.metadata.user_phone}}
3. IF → wallet exists AND last_activity > 24h ago → Stop (existing customer)
4. IF → NO wallet → 5. HTTP Request (Retry 3x) → Odoo CRM: Create lead
   Body: {
     "name": "Lead EcoCupon: {{ phone }}",
     "phone": "{{ phone }}",
     "source": "ecocupon_demo",
     "tag_ids": [reciclaje, cashback]
   }
6. WhatsApp → "👋 Hola! Vi que probaste EcoCupon. Te instalo esto en tu negocio en 24h. ¿Cuándo conversamos?"
```

---

## Workflow 5: REP Report Diario (FIX: query Supabase directo)

### Trigger
```
Cron: 8:00 AM CLT
```

### Nodes
```
1. Schedule → 8:00 AM
2. Supabase → Query directa:
   SELECT
     COUNT(*) as total_recycles,
     SUM(reward) as total_cashback,
     item,
     COUNT(DISTINCT phone) as unique_users
   FROM recycle_events
   WHERE created_at > NOW() - INTERVAL '1 day'
   GROUP BY item
3. HTTP Request → Supabase: INSERT events_log (log del reporte)
4. Email → Enviar reporte CSV a admin
5. WhatsApp → Resumen a admin: "📊 REP diario: {{total_recycles}} reciclajes, ${{total_cashback}} cashback, {{unique_users}} usuarios"
```

---

## Importar a n8n

1. Ir a `https://n8n.smarterbot.cl`
2. Crear nuevo workflow por cada uno arriba
3. Configurar webhook URL: `https://n8n.smarterbot.cl/webhook/ecocupon-agent`
4. Agregar error handling a cada workflow
5. Activar todos
6. Setear en `.env` del agent: `N8N_WEBHOOK_URL=https://n8n.smarterbot.cl/webhook/ecocupon-agent`
