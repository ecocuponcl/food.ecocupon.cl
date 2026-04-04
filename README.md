# 🌿 EcoCupon — IA Decision Engine

> "Convierte cualquier activo en dinero o cashback automáticamente"

---

## 🧠 Motor de Arbitraje

```
Input (foto/texto) → Agent /decide → n8n ejecuta → Supabase recuerda
```

### 3 Verticales, 1 Cerebro

| Vertical | Input | Output |
|---|---|---|
| ♻️ **RECYCLE** | Foto envase + QR | Cashback wallet |
| 🚗 **VEHICLE** | Patente + precio | Comprar / negociar / descartar |
| 🍔 **KIOSK** | Compra food | QR envases → cashback |

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    Caddy (HTTPS)                             │
│  food.ecocupon.cl → Odoo:8069                                │
│  agent.food.ecocupon.cl → Agent:9000                         │
│  n8n.smarterbot.cl → n8n:5678                                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  Agent /decide (cerebro)                     │
│                                                              │
│  LLM (OpenRouter) → scoring + reasoning                     │
│  Rules fallback → pricing tables                             │
│  Anti-fraud → limits + GPS + photo duplicate                │
│                                                              │
│  Output: JSON universal → n8n webhook                        │
└─────────────────────────────────────────────────────────────┘
         ↓              ↓              ↓
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  Supabase   │ │     n8n     │ │  Telegram   │
│  (memoria)  │ │  (event bus)│ │  (alertas)  │
│             │ │             │ │             │
│ events_log  │ │ route by    │ │ notifica    │
│ wallets     │ │ decision    │ │ confirma    │
│ recycle     │ │             │ │ reporta     │
│ vehicles    │ │             │ │             │
└─────────────┘ └─────────────┘ └─────────────┘
```

---

## 📦 Estructura

```
food.ecocupon.cl/
├── agent.py                    # FastAPI — IA Decision Engine v3
│   ├── POST /decide            # Universal decision endpoint
│   ├── POST /fraud-check       # Standalone fraud check
│   ├── POST /vehicle/evaluate  # Vehicle valuation
│   ├── POST /recycle/validate  # Recycle → cashback
│   ├── GET  /recycle/wallet    # Wallet balance
│   └── GET  /recycle/stats     # Platform stats
│
├── supabase/
│   └── schema.sql              # Full DB schema + RLS
│
├── n8n/
│   └── webhook-handler.md      # n8n workflow spec
│
├── odoo/
│   ├── food_kiosk/             # Kiosk module
│   └── eco_recycle/            # Recycle + cashback module
│
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🧠 Agent Schema — JSON Universal

```json
{
  "vertical": "RECYCLE | VEHICLE | KIOSK",
  "intent": "EVALUATE | ACTION | SUPPORT",
  "scoring": {
    "confidence": 0.9,
    "value_clp": 500,
    "reasoning": "PET 500ml detectado, limpio"
  },
  "decision": "approve | reject | review | comprar | negociar | descartar",
  "options": [
    {"action": "cashback", "amount": 500, "label": "+$500 CLP"}
  ],
  "metadata": {
    "event_id": "uuid",
    "user_phone": "56912345678"
  },
  "next_step": "n8n_triggered",
  "event_id": "uuid"
}
```

---

## 🛡️ Anti-Fraude

| Capa | Método | Qué evita |
|---|---|---|
| **QR único** | Token por envase, un solo uso | Reutilizar |
| **Límite diario** | Max $5.000 CLP / 10 reciclajes | Granjas |
| **Tiempo mínimo** | 15 min entre compra y reciclaje | Sin compra |
| **GPS clustering** | >5 usuarios mismo punto | Fake location |
| **Foto duplicada** | Hash comparison | Reuse photos |
| **LLM scoring** | IA detecta patrones anómalos | Fraude sofisticado |

---

## 🚀 Setup

### Agent (Mac local)
```bash
cd /Users/mac/dev/2026/food.ecocupon.cl
cp .env.example .env
# Editar .env con credenciales
pip install -r requirements.txt
uvicorn agent:app --reload --port 9000
```

### Supabase
```sql
-- Run supabase/schema.sql in SQL Editor
```

### n8n
```
Import webhook-handler.md workflows
Set webhook URL in .env
```

### Odoo
```
Copy odoo/eco_recycle/ to addons path
Install module from Apps
```

---

## 📊 Endpoints

| Endpoint | Método | Descripción |
|---|---|---|
| `/decide` | POST | Universal decision (3 verticals) |
| `/fraud-check` | POST | Standalone fraud scoring |
| `/vehicle/evaluate` | POST | Vehicle valuation |
| `/recycle/generate_qr` | POST | Generate QR tokens |
| `/recycle/validate` | POST | Validate → cashback |
| `/recycle/wallet/{phone}` | GET | Wallet balance |
| `/recycle/wallet/{phone}/withdraw` | POST | Withdraw balance |
| `/recycle/stats` | GET | Platform statistics |
| `/create_payment` | POST | Flow payment URL |
| `/health` | GET | Health + config status |

---

## 💰 Modelo de Negocio

| Plan | Precio | Incluye |
|---|---|---|
| **Básico** | $99.900/mes | Kiosk + Flow payments |
| **Reciclaje** | $199.900/mes | + Cashback + Wallet + REP |
| **Enterprise** | $399.900/mes | + Multi-sucursal + AI fraud |

---

## 🌐 URLs

| Servicio | URL |
|---|---|
| Kiosk | `https://food.ecocupon.cl/kiosk` |
| Agent API | `https://agent.food.ecocupon.cl` |
| Swagger | `https://agent.food.ecocupon.cl/docs` |
| n8n | `https://n8n.smarterbot.cl` |
| Admin Odoo | `https://food.ecocupon.cl/web/login` |
