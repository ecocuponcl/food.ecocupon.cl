# 💰 MOTOR DE CONTABILIDAD Y PAGOS — SmarterOS v6.0

> **"Si no paga, no tiene acceso"** — Todos los bots de SmarterOS son canales de cobro.

---

## 🏗️ Arquitectura del Flujo

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     FLUJO DE COBRO POR TENANT                             │
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐            │
│  │  Telegram    │    │   MiniApp    │    │    Dashboard     │            │
│  │  Bot per     │───▶│  per Tenant  │───▶│  Key Confirm     │            │
│  │  Tenant      │    │  (Web)       │    │  (Streamlit)     │            │
│  └──────┬───────┘    └──────┬───────┘    └────────┬─────────┘            │
│         │                   │                      │                      │
│         └───────────────────┼──────────────────────┘                      │
│                             ▼                                             │
│              ┌──────────────────────────┐                                 │
│              │   n8n: Motor de Cobros   │                                 │
│              │                          │                                 │
│              │  1. Validar tenant       │                                 │
│              │  2. Verificar pago       │                                 │
│              │  3. Si NO paga → Bloquear│                                 │
│              │  4. Si SÍ paga → Activar │                                 │
│              │  5. Emitir DTE (SII)     │                                 │
│              │  6. Registrar contable   │                                 │
│              └────────────┬─────────────┘                                 │
│                           ▼                                               │
│              ┌──────────────────────────┐                                 │
│              │   Payment Gateway        │                                 │
│              │   (Flow.cl / MercadoPago)│                                 │
│              └────────────┬─────────────┘                                 │
│                           ▼                                               │
│              ┌──────────────────────────┐                                 │
│              │   PostgreSQL             │                                 │
│              │   - checkouts            │                                 │
│              │   - inventory            │                                 │
│              │   - smarter_rule_log     │                                 │
│              │   - funnel_metrics       │                                 │
│              └──────────────────────────┘                                 │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Tenants y Sus Bots

| Tenant | Bot Telegram | MiniApp URL | Dashboard Key | Plan Mensual |
|--------|-------------|-------------|---------------|-------------|
| `ecocupon_cl` | @EcoCuponBot | `https://ecocupon.cl/app` | `ECO-CL-KEY` | $199.900 CLP |
| `ecocupon_mza` | @EcoCuponMzaBot | `https://mza.ecocupon.cl/app` | `ECO-MZA-KEY` | $199.900 ARS |
| `food_kiosk` | @FoodKioskBot | `https://food.ecocupon.cl/app` | `FOOD-KS-KEY` | $99.900 CLP |
| `smarter_prop` | @SmarterPropBot | `https://prop.smarterbot.store/app` | `PROP-KEY` | $399.900 CLP |
| `smarter_store` | @SmarterStoreBot | `https://smarterbot.store/app` | `STORE-KEY` | $499.900 CLP |

---

## ⚙️ Reglas de Cobro (RULE_31 a RULE_40)

| Regla | Nombre | Trigger | Acción |
|-------|--------|---------|--------|
| 31 | `daily_telegram_recap` | Daily 9AM | Recap ventas del día |
| 32 | `incident_alert` | Error 5xx | Alerta + pausa servicio |
| 33 | `whatsapp_concierge` | WhatsApp msg | Redirect a cobro |
| 34 | `anomaly_detection` | Pago fuera patrón | Flag para review |
| 35 | `predictive_maintenance` | 7 días sin pago | Recordatorio |
| 36 | `voice_to_command` | Voice msg | Parse → cobro |
| 37 | `multi_node_sync` | Pago en un nodo | Sync a todos |
| 38 | `tenant_onboarding` | Nuevo tenant | Setup cobro auto |
| 39 | `billing_alert` | Stock < threshold | Alerta inventario |
| 40 | `ai_optimizer` | Mensual | Optimizar pricing |

---

## 🔑 Principio: "SINO NADA ES GRATIS"

```
Usuario escanea QR o abre MiniApp
         ↓
¿Tenant tiene pago activo?
    ├── SÍ → Servicio normal
    └── NO → 
         ├── Generar orden de pago
         ├── Enviar link Flow.cl / MercadoPago
         ├── Esperar confirmación webhook
         └── Una vez pagado → Activar servicio
```

---

## 💾 Tablas DB Involucradas

| Tabla | Propósito |
|-------|-----------|
| `checkouts` | Registro de cada intento de pago |
| `inventory` | Stock de productos/QR por tenant |
| `funnel_metrics` | Conversión QR → pago |
| `smarter_rules` | Definición de reglas de cobro |
| `smarter_rule_log` | Log de ejecución de reglas |
| `smarter_pairings` | Sesiones de acceso por tenant |

---

## 🚀 Webhook Endpoints (n8n)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/webhook/payment/checkout` | POST | Checkout desde MiniApp o Telegram |
| `/webhook/payment/confirm` | POST | Confirmación de pago desde Flow.cl |
| `/webhook/telegram/billing` | POST | Comando de cobro desde bot |
| `/webhook/dashboard/activate` | POST | Activación de key desde dashboard |

---

## 📊 Dashboard de Confirmación

El Bolt Dashboard muestra:
- ✅ Tenant activo / ❌ Tenant suspendido
- 💰 Revenue del mes actual
- 📈 Tasa de conversión (QR → pago)
- ⚠️ Alertas de inventario (RULE_39)
- 🔑 Keys activas por tenant

---

## 🔄 Flujo Completo Paso a Paso

### 1. Usuario escanea QR o abre MiniApp
```
POST /webhook/payment/checkout
{
  "tenant_slug": "ecocupon_cl",
  "product_id": "ECO-KIT-001",
  "quantity": 1,
  "source_channel": "telegram",
  "tenant_chat_id": "6683244662"
}
```

### 2. n8n valida si el tenant tiene pago activo
```
Query: SELECT * FROM smarter_pairings WHERE tenant_slug = 'ecocupon_cl'
→ Si NO tiene pago → Generar orden
```

### 3. Generar orden de pago
```json
{
  "status": "payment_required",
  "order_id": "PAY-1712500000-ABC123",
  "payment_url": "https://flow.cl/btn.php?token=ORDER_PAY-1712500000-ABC123",
  "next_step": "redirect_to_payment"
}
```

### 4. Usuario paga → Flow.cl confirma
```
POST /webhook/payment/confirm
{
  "order_id": "PAY-1712500000-ABC123",
  "status": "completed",
  "amount": 199900,
  "tenant_slug": "ecocupon_cl"
}
```

### 5. n8n procesa confirmación
- ✅ Actualiza `checkouts` table
- ✅ Emite DTE (boleta electrónica)
- ✅ Actualiza `funnel_metrics`
- ✅ Log en `smarter_rule_log` (RULE_39)
- ✅ Notifica Telegram al tenant

---

## 💻 Comandos Telegram para Cobros

| Comando | Descripción |
|---------|-------------|
| `/billing` | Ver estado de pago del tenant |
| `/pay` | Generar link de pago |
| `/invoice` | Ver facturas emitidas |
| `/rule 39` | Check inventario y alertas |
| `/status` | Estado general del tenant |

---

## 📁 Archivos Creados

```
n8n-workflows/
├── 60-payment-engine-complete.json    ← Workflow n8n completo
└── PAYMENT-ENGINE-README.md          ← Documentación
```
