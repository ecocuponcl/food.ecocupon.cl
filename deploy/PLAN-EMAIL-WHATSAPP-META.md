# 🚀 EMAIL MARKETING + WHATSAPP + META — Plan Completo

## 📊 ESTADO ACTUAL

| Componente | Estado | Acción |
|-----------|--------|--------|
| **Mailgun** | ⚠️ Key 403 | Necesita nueva key desde dashboard |
| **n8n workflows** | ✅ 7 activos | Falta email marketing |
| **LLM API** | ✅ 200 | llm.smarterbot.store/ai/qwen |
| **Telegram Bot** | ✅ Activo | 7631713367 |
| **WhatsApp Business** | ❌ Sin Meta | Crear cuenta Meta Business |
| **Odoo CRM** | ✅ Listo | food_kiosk DB |

---

## 🔥 PLAN EJECUTABLE

### PASO 1: Email Marketing CLAWBOT (30 min)

**Workflow n8n:** `WF-EMAIL-01`
- Trigger: Telegram `/cotizar CLAWBOT`
- LLM genera respuesta personalizada
- Envía Telegram + Email
- Crea lead en Odoo

**Template Email:**
```
Asunto: ️ Tu Cotización CLAWBOT Kiosk - SmarterOS

Contenido:
- Imagen CLAWBOT
- Precio: $950.000 setup + $190.000/mes
- Incluye: Hardware + Software + Odoo + n8n + OpenClaw
- Cupón: MECANICO15 (15% OFF)
- CTA: Pagar ahora → odoo.ecocupon.cl
- Footer: WhatsApp + Telegram
```

### PASO 2: Meta Business + WhatsApp API (1-7 días)

**Crear cuenta Meta Business:**
1. Ir a https://business.facebook.com
2. Crear cuenta de empresa
3. Verificar:
   - RUT empresa
   - Dirección
   - Teléfono
   - Sitio web (ecocupon.cl)
4. Crear App WhatsApp
5. Obtener:
   - Phone Number ID
   - Access Token
   - Verify Webhook

**Configurar Webhook:**
```
URL: https://n8n.smarterbot.store/webhook/whatsapp-in
Verify Token: smarterbot-whatsapp-2026
```

### PASO 3: WhatsApp → LLM Integration (1 hora)

**Flujo:**
```
WhatsApp mensaje → Webhook n8n → LLM → Respuesta WhatsApp
```

**Payload LLM:**
```json
POST https://llm.smarterbot.store/ai/qwen
{
  "model": "qwen/qwen-2.5-72b-instruct",
  "messages": [
    {"role": "system", "content": "Vendedor SmarterOS..."},
    {"role": "user", "content": "Hola, quiero cotizar CLAWBOT"}
  ]
}
```

**Prompt Sistema LLM:**
```
Eres vendedor experto SmarterOS.
Productos:
- CLAWBOT Kiosk: $950.000 setup + $190.000/mes (25 UF + 5 UF)
- Hosting: $190.000 setup + $76.000/mes (5 UF + 2 UF)
- SmarterOS Sub: $380.000/mes (10 UF)
- OpenClaw: $114.000/mes (3 UF)

Reglas:
1. Responde en español
2. Siempre da precio en UF y CLP
3. Menciona cupón MECANICO15 (15% OFF)
4. Cierra con pregunta: "¿Te interesa?"
5. Si compra → envía link odoo.ecocupon.cl
```

---

## ⚡ MVP INMEDIATO (HOY sin Meta)

### 1. Telegram → LLM → Cotización ✅
```
Usuario: /cotizar CLAWBOT
    ↓
n8n parsea → LLM responde
    ↓
Telegram: Cotización completa
```

### 2. Email Marketing (manual hasta arreglar Mailgun)
```
n8n genera email HTML
    ↓
Enviar manualmente hasta que Mailgun funcione
    ↓
O usar SendGrid/otro proveedor
```

### 3. WhatsApp Manual (wa.me links)
```
Bot Telegram genera link:
https://wa.me/56979540471?text=Cotización+CLAWBOT

Cliente hace click → WhatsApp abre
```

### 4. Meta Business (configurar ahora, activar después)
```
Crear cuenta → Verificar → Esperar aprobación → Activar API
```

---

## 📧 EMAIL TEMPLATES

### Template 1: Cotización CLAWBOT
```html
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; }
    .header { background: #FFF159; padding: 20px; text-align: center; }
    .product { background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 8px; }
    .price { font-size: 24px; font-weight: bold; color: #3483FA; }
    .cta { background: #3483FA; color: white; padding: 15px 30px; 
           border-radius: 6px; text-decoration: none; display: inline-block; }
    .coupon { background: #00A650; color: white; padding: 10px; 
              border-radius: 4px; text-align: center; font-size: 18px; }
  </style>
</head>
<body>
  <div class="header">
    <h1>🖥️ Tu Cotización CLAWBOT</h1>
  </div>
  
  <div class="product">
    <h2>CLAWBOT Kiosk Completo</h2>
    <p class="price">$950.000 CLP</p>
    <p>Setup: 25 UF | Mensual: 5 UF ($190.000/mes)</p>
    <ul>
      <li>✅ Hardware + Pantalla táctil</li>
      <li>✅ Software personalizado</li>
      <li>✅ Integración Odoo ERP</li>
      <li>✅ Automatización n8n</li>
      <li>✅ IA OpenClaw</li>
      <li>✅ Soporte 24/7</li>
    </ul>
  </div>
  
  <div class="coupon">
    🎁 Cupón: MECANICO15 → 15% OFF = $807.500
  </div>
  
  <p style="text-align: center; margin: 20px 0;">
    <a href="https://odoo.ecocupon.cl/web/login" class="cta">
      Pagar Ahora →
    </a>
  </p>
  
  <p style="text-align: center; color: #666;">
    ¿Dudas? WhatsApp: +56979540471 | Telegram: @SmarterBotCl
  </p>
</body>
</html>
```

---

## 🔗 LINKS IMPORTANTES

| Servicio | URL |
|----------|-----|
| Meta Business | https://business.facebook.com |
| WhatsApp API Docs | https://developers.facebook.com/docs/whatsapp |
| Mailgun Dashboard | https://app.mailgun.com |
| n8n Workflows | https://n8n.smarterbot.store |
| LLM API | https://llm.smarterbot.store/docs |
| Odoo CRM | https://odoo.ecocupon.cl/web/login |

---

## ⚠️ ACCIONES REQUERIDAS

### Urgente (hoy):
1. ✅ Crear workflow n8n email marketing (listo en wf-email-cotizacion-clawbot.json)
2. ⏳ Arreglar Mailgun key (403 Forbidden)
3. ⏳ Importar workflow a n8n

### Esta semana:
4. ⏳ Crear Meta Business Account
5. ⏳ Verificar negocio (RUT, dirección)
6. ⏳ Configurar WhatsApp Business API
7. ⏳ Conectar WhatsApp → n8n → LLM

### Pendiente:
8. ⏳ Template email HTML final
9. ⏳ Testing end-to-end
10. ⏳ Lanzamiento

---

## 💰 MÉTRICAS EMAIL MARKETING

| Métrica | Semana 1 | Semana 4 |
|---------|----------|----------|
| Emails enviados | 50 | 500 |
| Tasa apertura | 25% | 40% |
| Tasa click | 8% | 15% |
| Cotizaciones | 5 | 50 |
| Conversiones | 1 | 10 |
| Revenue | $950.000 | $9.500.000 |

---

## 🎯 RESUMEN EJECUTIVO

**HOY:**
- Telegram bot cotiza con LLM ✅
- Email template listo ✅
- Workflow n8n creado ✅
- Falta: Mailgun key nueva

**SEMANA 1:**
- Meta Business creado
- WhatsApp API configurado
- Email marketing automático

**SEMANA 2:**
- Todo integrado
- Flujo completo operativo
- Métricas trackeadas
