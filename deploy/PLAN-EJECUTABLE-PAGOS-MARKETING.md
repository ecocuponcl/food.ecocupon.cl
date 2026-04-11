# 🚀 PLAN EJECUTABLE: Odoo + Pagos + Email Marketing + Omnicanal

## 📊 ESTADO ACTUAL (auditado)

| Componente | Estado | Problema |
|-----------|--------|----------|
| **Odoo v19** | ✅ food-odoo:8070 activo | - |
| **erp/odoo.smarterbot.store** | ❌ 502 | Cloudflare no conecta (zona externa) |
| **Módulos pago** | ❌ 0 instalados | Sin MercadoPago, Flow.cl |
| **Email marketing** | ❌ No configurado | Sin templates ni workflows |
| **MercadoLibre API** | ❌ Sin integrar | Sin webhook de compras |

---

## 🔥 PRIORIDAD 1: ACCESO A ODOO (15 min)

### Problema
`odoo.smarterbot.store` → Cloudflare (zona ajena) → 502

### Solución: Crear dominio alternativo que controlamos
```
Opción A: odoo.ecocupon.cl → 89.116.23.167 (DNS directo, sin proxy)
Opción B: erp.ecocupon.cl → 89.116.23.167
Opción C: Acceso directo http://89.116.23.167:8070
```

### Fix inmediato (Opción A - 5 min)
1. Crear DNS A record en Cloudflare ecocupon.cl:
   - Name: `odoo`
   - Content: `89.116.23.167`
   - Proxy: **DNS only** (grey cloud)
2. Agregar a Caddyfile: `odoo.ecocupon.cl` → `127.0.0.1:8070`
3. Caddy obtiene certificado automáticamente

---

## 💳 PRIORIDAD 2: MÓDULOS DE PAGO (1 hora)

### 2.1 MercadoPago para Odoo v19
```
Opción A: Módulo oficial Odoo (si disponible v19)
Opción B: Módulo community GitHub
Opción C: Integración directa vía API (n8n webhook)

Recomendado: Opción C (más rápido, sin depender de módulo Odoo)
  n8n escucha webhook de MP → crea factura en Odoo → envía confirmación
```

### 2.2 Flow.cl (versión legacy compatible)
```
Buscar módulo Flow.cl para Odoo 16-17
Adaptar imports para Odoo 19
O: Integración vía API (similar a MP)
```

### 2.3 Transferencia Bancaria (nativo Odoo)
```
Ya disponible: account_payment module
Configurar:
  - Banco: [Tu banco]
  - Cuenta: [Número]
  - Rut empresa: [RUT]
  - Instrucciones de pago
```

---

## 📧 PRIORIDAD 3: EMAIL MARKETING (2 horas)

### 3.1 Estructura de campaña
```
Trigger: Usuario compra OBD2 en MercadoLibre
  ↓
Email 1 (inmediato):
  Asunto: "¿Sabías que puedes llevar el mecánico a tu casa? 🔧"
  Contenido:
    - Video del OBD2 que compró
    - "Con SmarterOS, tu auto se diagnostica solo"
    - Cupón: MECANICO15 (15% off primera consulta)
    - Link: https://odoo.ecocupon.cl/app/mecanico-domicilio
  ↓
Email 2 (3 días):
  Asunto: "Tu auto necesita esto 🚗"
  Contenido:
    - Productos complementarios sugeridos
    - "Completa tu kit de diagnóstico"
    - Cupón expira en 7 días
  ↓
Email 3 (7 días):
  Asunto: "⏰ Última oportunidad - 15% off"
  Contenido:
    - Urgencia
    - Testimonios
    - Link directo a compra
```

### 3.2 Integración MercadoLibre API
```python
# n8n workflow:
1. Webhook ML: nueva compra detectada
2. GET /users/{user_id}/purchases → obtener producto
3. Buscar productos complementarios:
   GET /sites/MLC/search?category={category}&q={related}
4. Generar email HTML personalizado
5. Enviar vía Mailgun
6. Registrar en Odoo CRM
7. Trackear apertura/clicks
```

### 3.3 Template HTML Email
```html
<!-- Video del producto ML -->
<div class="product-video">
  <iframe src="{{ml_video_url}}"></iframe>
</div>

<!-- Cupón -->
<div class="coupon">
  MECANICO15 - 15% OFF
</div>

<!-- CTA -->
<a href="https://odoo.ecocupon.cl/shop/mecanico-domicilio">
  Agenda tu mecánico a domicilio
</a>
```

---

## 🌐 PRIORIDAD 4: OMNICANAL (1 hora)

### 4.1 Flujo completo
```
ML compra → n8n detecta → BOLT genera oferta
  ↓
Email (Mailgun) → Video + Cupón
WhatsApp (Twilio) → Link directo
Telegram (Bot) → Recordatorio
SMS → Urgencia 48h
  ↓
BOLT repite hasta conversión o 30 días
```

### 4.2 "Mecánico a Domicilio" App
```
Concepto: "¿Quieres un mecánico en tu casa?"
  ↓
Web app simple (HTML/JS):
  1. Ingresa patente
  2. Selecciona servicio
  3. Elige fecha/hora
  4. Paga online (MercadoPago/Flow)
  5. Mecánico llega a domicilio
  ↓
Integración:
  - Odoo CRM: crea oportunidad
  - Odoo Calendar: agenda visita
  - Odoo Invoicing: genera factura
  - Telegram: notifica al mecánico
```

---

## 📦 PRIORIDAD 5: CAJA DIARIA + APRENDIZAJE

### 5.1 Daily Box
```
Cada día a las 23:59:
  1. Ingestar: ventas, leads, emails, clicks
  2. Calcular: conversión, revenue, churn
  3. Ajustar: precios UF, cupones, mensajes
  4. Reportar: Telegram resumen diario
  5. Aprender: qué funcionó, qué no
```

### 5.2 Skills Nuevas
```
Semana 1: Email marketing básico ✅
Semana 2: Segmentación por comportamiento
Semana 3: Predicción churn con IA
Semana 4: Optimización automática precios
```

---

## ⚡ EJECUCIÓN INMEDIATA (HOY - 4 horas)

| Hora | Tarea | Estado |
|------|-------|--------|
| 0:00-0:15 | Fix DNS odoo.ecocupon.cl | ⏳ |
| 0:15-0:30 | Configurar Caddy + SSL | ⏳ |
| 0:30-1:00 | Instalar módulos pago Odoo | ⏳ |
| 1:00-1:30 | Configurar MercadoPago API | ⏳ |
| 1:30-2:00 | Crear template email marketing | ⏳ |
| 2:00-2:30 | Workflow n8n: ML → Email | ⏳ |
| 2:30-3:00 | Configurar cupones Odoo | ⏳ |
| 3:00-3:30 | Test flujo completo | ⏳ |
| 3:30-4:00 | Documentar + commit | ⏳ |

---

## 🎯 MÉTRICAS DE ÉXITO

| Métrica | Semana 1 | Semana 4 |
|---------|----------|----------|
| Emails enviados | 100 | 2,000 |
| Tasa apertura | 20% | 35% |
| Tasa click | 5% | 12% |
| Conversiones | 1 | 20 |
| Revenue mensual | 0.17 UF | 3.4 UF |

---

## 📁 ARCHIVOS A CREAR

```
/opt/smarterbot/
├── odoo-mercadopago/          # Integración MP
│   ├── webhook_listener.py
│   ├── payment_processor.py
│   └── config.json
├── email-marketing/
│   ├── templates/
│   │   ├── obd2-welcome.html
│   │   ├── mechanic-home.html
│   │   └── coupon-expiring.html
│   └── campaign_config.json
├── mercadolibre-integration/
│   ├── ml_api_client.py
│   ├── product_recommender.py
│   └── purchase_webhook.py
└── n8n-workflows/
    ├── ml-purchase-email.json
    ├── coupon-generator.json
    └── omnichannel-dispatcher.json
```

---

## 🚀 PRÓXIMO PASO INMEDIATO

**¿Por dónde empezamos?**

1. **Fix Odoo acceso** (DNS + Caddy) → 15 min
2. **Instalar MercadoPago** → 30 min
3. **Primer email marketing** → 1 hora

**Recomiendo empezar por 1 → 2 → 3 en orden.**
