# n8n WhatsApp Workflows — EcoCupon

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
```

---

## Workflow 1: Reciclaje → WhatsApp

### Trigger
```
Webhook: POST /webhook/ecocupon-agent
Body: { vertical: "RECYCLE", decision: "approve", scoring: { value_clp: 50 }, metadata: { user_phone: "56912345678" } }
```

### Nodes
```
1. Webhook → recibe evento
2. Switch → filtra vertical = "RECYCLE"
3. IF → decision = "approve"
   ├─ YES → 4. HTTP Request → WhatsApp API
   │         Body: {
   │           "messaging_product": "whatsapp",
   │           "to": "{{ $json.metadata.user_phone }}",
   │           "type": "template",
   │           "template": {
   │             "name": "ecocupon_recycle",
   │             "language": { "code": "es" },
   │             "components": [{
   │               "type": "body",
   │               "parameters": [
   │                 { "type": "text", "text": "{{ $json.scoring.value_clp }}" },
   │                 { "type": "text", "text": "{{ $json.scoring.reasoning }}" }
   │               ]
   │             }]
   │           }
   │         }
   │
   └─ NO → 5. IF → decision = "reject"
             ├─ YES → WhatsApp: "❌ Reciclaje rechazado: {{ $json.scoring.reasoning }}"
             └─ NO → WhatsApp: "⚠️ Tu reciclaje está en revisión"
```

### Template WhatsApp (Meta)
```
Nombre: ecocupon_recycle
Idioma: es
Cuerpo: "♻️ +${{1}} CLP por reciclar\n{{2}}\n\nSaldo actual: consulta en ecocupon.cl"
```

---

## Workflow 2: Vehículo → WhatsApp

### Trigger
```
Webhook: POST /webhook/ecocupon-agent
Body: { vertical: "VEHICLE", decision: "negociar", scoring: { value_clp: 3900000 }, data: { marca: "Toyota", modelo: "Yaris", ano: 2019 } }
```

### Nodes
```
1. Webhook → recibe evento
2. Switch → filtra vertical = "VEHICLE"
3. Switch → decision:
   ├─ "comprar" → WhatsApp: "🚗 {{marca}} {{modelo}} {{ano}} a buen precio (${{value_clp}}). ¿Agendar visita?"
   ├─ "negociar" → WhatsApp: "💡 {{marca}} {{modelo}} → Valor real: ${{value_clp}}. Precio sugerido: ${{suggested}}. ¿Enviar oferta?"
   └─ "descartar" → WhatsApp: "⚠️ {{marca}} {{modelo}} sobreprecio. Alternativa reciclaje: ${{recycle_value}}"
```

### Template WhatsApp
```
Nombre: ecocupon_vehicle
Idioma: es
Cuerpo: "🚗 {{1}} {{2}} {{3}}\nValor estimado: ${{4}}\nDecisión: {{5}}\n\nVer detalle: ecocupon.cl/vehiculos"
```

---

## Workflow 3: Kiosk → WhatsApp

### Trigger
```
Webhook: POST /webhook/ecocupon-agent
Body: { vertical: "KIOSK", decision: "qr_generated", total_cashback: 200, metadata: { user_phone: "56912345678" } }
```

### Nodes
```
1. Webhook → recibe evento
2. Switch → filtra vertical = "KIOSK"
3. HTTP Request → WhatsApp API
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

### Template WhatsApp
```
Nombre: ecocupon_kiosk
Idioma: es
Cuerpo: "🍔 Tu pedido generó ${{1}} CLP en cashback\n{{2}} envases reciclables\n\nEscanea los QR en tu ticket para recibir el dinero"
```

---

## Workflow 4: Lead → Odoo CRM

### Trigger
```
Webhook: POST /webhook/ecocupon-agent
Cualquier evento con metadata.user_phone
```

### Nodes
```
1. Webhook → recibe evento
2. Supabase → Check if phone exists in wallets
   ├─ EXISTS → Update last_activity
   └─ NEW → 3. HTTP Request → Odoo CRM
              Create lead: {
                "name": "Lead EcoCupon: {{ phone }}",
                "phone": "{{ phone }}",
                "source": "ecocupon_demo",
                "tag_ids": [reciclaje, cashback]
              }
4. WhatsApp → "👋 Hola! Vi que probaste EcoCupon. Te instalo esto en tu negocio en 24h. ¿Cuándo conversamos?"
```

---

## Workflow 5: REP Report Diario

### Trigger
```
Cron: 8:00 AM CLT
```

### Nodes
```
1. Schedule → 8:00 AM
2. Supabase → Query:
   SELECT COUNT(*), SUM(reward), item FROM recycle_events
   WHERE created_at > NOW() - INTERVAL '1 day'
   GROUP BY item
3. HTTP Request → Agent /generate_rep
4. Email → Enviar reporte a admin
5. WhatsApp → Resumen a admin: "📊 REP diario: {{count}} reciclajes, ${{total}} cashback"
```

---

## Importar a n8n

1. Ir a `https://n8n.smarterbot.cl`
2. Crear nuevo workflow por cada uno arriba
3. Configurar webhook URL: `https://n8n.smarterbot.cl/webhook/ecocupon-agent`
4. Activar todos
5. Setear en `.env` del agent: `N8N_WEBHOOK_URL=https://n8n.smarterbot.cl/webhook/ecocupon-agent`
