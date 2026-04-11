# 🚀 PLAN: SmarterOS Payment + Email Marketing + Omnicanal

## PROBLEMAS ACTUALES
1. ❌ `odoo.smarterbot.store` → 502 Cloudflare (no conecta al backend)
2. ❌ Sin módulos de pago en Odoo (MercadoPago, Flow.cl)
3. ❌ Sin email marketing configurado
4. ❌ Sin integración MercadoLibre para sugerir productos

---

## FASE 1: FIX ODOO + PAGOS (2 horas)

### 1.1 Fix odoo.smarterbot.store 502
```
Problema: Cloudflare no resuelve al VPS
Fix: DNS A record → 89.116.23.167 (proxy OFF primero, luego ON)
```

### 1.2 Instalar módulos de pago en Odoo v19
```
a) MercadoPago (oficial Odoo o community)
   - Descargar módulo compatible Odoo 19
   - Configurar credentials (client_id, client_secret)
   
b) Flow.cl (versión legacy compatible)
   - Buscar versión v16/v17 que funcione en v19
   - Configurar API key, secret, commerce_code
   
c) Transferencia Bancaria (nativo Odoo)
   - Configurar cuenta bancaria CL
   - Activar pago por transferencia
```

### 1.3 Configurar productos en Odoo
```
- CLAWBOT Kiosk: 25 UF setup + 5 UF/mes
- Hosting: 5 UF setup + 2 UF/mes  
- Kiosk Setup: 15 UF setup + 3 UF/mes
- SmarterOS Sub: 10 UF/mes
- OpenClaw Agent: 3 UF/mes
```

---

## FASE 2: EMAIL MARKETING (3 horas)

### 2.1 Estructura de campaña
```
Trigger: Usuario compra producto en ML (ej: OBD2 scanner)
  ↓
Email 1 (inmediato): "¿Sabías que puedes llevar el mecánico a tu casa?"
  - Video del producto comprado
  - Cupón 15% descuento
  - Link a app "Mecánico a Domicilio"
  ↓
Email 2 (3 días): "Tu auto necesita esto"
  - Productos sugeridos basados en compra anterior
  - Ofertas personalizadas
  ↓
Email 3 (7 días): "Última oportunidad"
  - Cupón expira en 48h
  - Urgencia + escasez
```

### 2.2 Integración MercadoLibre
```
API ML → obtener historial de compras del usuario
  ↓
ML API: /users/{user_id}/purchases
  ↓
Extraer categorías: Autos, Electrónica, Hogar
  ↓
Generar emails personalizados con:
  - Productos similares
  - Complementarios
  - Cupones personalizados
```

### 2.3 n8n Workflow: Email Marketing
```
Webhook ML (nueva compra detectada)
  ↓
Parsear producto comprado
  ↓
Buscar productos complementarios en ML API
  ↓
Generar email HTML con video/imagen del producto
  ↓
Enviar vía Mailgun/SendGrid
  ↓
Registrar en Odoo CRM
  ↓
Trackear apertura/clicks
  ↓
Si abrió → enviar cupón por Telegram
  ↓
Si compró → activar servicio SmarterOS
```

---

## FASE 3: OMNICANAL (2 horas)

### 3.1 Flujo completo
```
ML compra → n8n detecta → BOLT genera oferta personalizada
  ↓
Omnicanal:
  1. Email con video del producto
  2. WhatsApp con cupón QR
  3. Telegram con link directo
  4. SMS recordatorio 24h
  ↓
BOLT repite secuencia hasta conversión
```

### 3.2 "Mecánico a Domicilio" Concept
```
App/Web: "¿Quieres un mecánico en tu casa?"
  ↓
Escaneo OBD2 remoto (vía app)
  ↓
Diagnóstico automático por IA
  ↓
Cotización instantánea en UF
  ↓
Agendar visita + pago online
  ↓
Mecánico llega con repuestos (sugeridos por ML)
```

### 3.3 Cupón de Descuento
```
Cupón: BIENVENIDO15 (15% off primera compra)
  ↓
Integrado con:
  - MercadoPago checkout
  - Flow.cl redirect
  - Odoo invoice auto-generate
  ↓
Tracking:
  - cupón usado → Odoo registra venta
  - n8n dispara welcome sequence
  - BOLT agrega a pipeline de retención
```

---

## FASE 4: CAJA DIARIA + APRENDIZAJE (continuo)

### 4.1 Daily Box
```
Cada día:
  1. Ingestar datos: ventas, leads, emails abiertos
  2. Calcular métricas: conversión, revenue, churn
  3. Ajustar precios UF según mercado
  4. Generar reportes automáticos
  5. Enviar resumen por Telegram
```

### 4.2 Skills Nuevas (auto-aprendizaje)
```
Semana 1: Email marketing básico
Semana 2: Segmentación avanzada ML
Semana 3: Predicción de churn con IA
Semana 4: Optimización automática de precios
```

---

## EJECUCIÓN INMEDIATA (HOY)

### Prioridad 1: Fix Odoo 502
```bash
# Crear DNS record para odoo.smarterbot.store
# Verificar Caddy config
# Test HTTPS
```

### Prioridad 2: Instalar MercadoPago en Odoo
```bash
# Descargar módulo
# Instalar via Odoo UI
# Configurar credentials
# Test payment flow
```

### Prioridad 3: Primer email marketing
```bash
# Configurar Mailgun domain
# Crear template HTML
# Enviar primer test
```

---

## TIMELINE
| Día | Tarea | Tiempo |
|-----|-------|--------|
| Hoy | Fix Odoo 502 + MP module | 2h |
| Hoy | Configurar Flow.cl | 1h |
| Mañana | Email marketing template | 2h |
| Mañana | Integración ML API | 2h |
| Día 3 | Omnicanal setup | 3h |
| Día 3 | Test completo | 1h |

---

## METAS
- Semana 1: 100 emails enviados → 20 aperturas → 5 clicks → 1 venta
- Semana 2: 500 emails → 100 aperturas → 25 clicks → 5 ventas
- Semana 4: 2000 emails → 500 aperturas → 100 clicks → 20 ventas
- Revenue: 20 ventas × 0.17 UF/mes = 3.4 UF/mes recurrente
