# 🚀 Food Ecocupon — Kiosk + Odoo + Flow.cl

Kiosk táctil para pedidos con pagos reales integrados via Flow.cl.

---

## Arquitectura

```
food.ecocupon.cl  →  VPS (Odoo 17 + Caddy)
agent.food.ecocupon.cl  →  Cloudflare Tunnel  →  Mac (FastAPI Agent)  →  Flow.cl
```

## Flujo de pago

1. Usuario selecciona productos en kiosko táctil
2. Touch "Pagar" → Odoo crea orden
3. Odoo → `agent.food.ecocupon.cl/create_payment`
4. Agente → Flow.cl API
5. Flow.cl devuelve URL de pago
6. Usuario paga en navegador
7. Flow.cl → webhook → Odoo confirma orden

---

## 📦 Estructura

```
food.ecocupon.cl/
├── food_kiosk/                    # Módulo Odoo
│   ├── controllers/kiosk_controller.py   # /kiosk, /kiosk/create_order, /kiosk/payment_webhook
│   ├── models/kiosk_config.py           # Settings configurables
│   ├── views/food_kiosk_templates.xml   # QWeb templates UI
│   ├── static/src/css/kiosk.css         # Estilos kiosk vertical
│   ├── static/src/js/kiosk.js           # Cart + payment JS
│   └── ...
├── agent/                          # FastAPI Agent (Mac local)
│   └── agent.py                    # Proxy Flow.cl API
├── deploy/                         # VPS deployment
│   ├── docker-compose.yml          # Odoo 17 + Postgres 16
│   └── Caddyfile.snippet           # Caddy config
└── README.md
```

---

## 🖥️ Deploy VPS (Dokploy + Caddy)

### Odoo
```bash
cd /root/food-kiosk-deploy
docker compose up -d
```

### Caddy
```
food.ecocupon.cl {
    reverse_proxy localhost:8070
}
```

### DNS
```
food.ecocupon.cl  →  A  →  89.116.23.167  (nube gris, sin proxy CF)
```

---

## 🧠 Agente (Mac local)

```bash
pip install fastapi uvicorn requests

# agent.py
from fastapi import FastAPI
import requests

app = FastAPI()
FLOW_API = "https://www.flow.cl/api/payment/create"
FLOW_KEY = "TU_API_KEY"

@app.post("/create_payment")
def create_payment(data: dict):
    r = requests.post(FLOW_API, json={
        "apiKey": FLOW_KEY,
        "amount": data["amount"],
        "subject": f"Pedido {data['order_id']}",
        "return_url": "https://food.ecocupon.cl/kiosk/return",
        "confirm_url": "https://food.ecocupon.cl/kiosk/payment_webhook"
    })
    res = r.json()
    return {"url": res.get("url"), "token": res.get("token")}

# Correr
uvicorn agent:app --host 0.0.0.0 --port 9000
```

### Cloudflare Tunnel
```bash
brew install cloudflared
cloudflared tunnel login
cloudflared tunnel create ecocupon-agent
cloudflared tunnel run ecocupon-agent
```

---

## ✅ Checklist

- [x] Odoo corriendo con food_kiosk
- [x] Caddy HTTPS configurado
- [x] DNS apuntando al VPS
- [x] Certificado SSL Let's Encrypt válido
- [ ] Mac encendida + agent.py corriendo
- [ ] Cloudflare Tunnel activo
- [ ] Flow.cl API key configurada
- [ ] `agent.food.ecocupon.cl` responde

---

## Endpoints

| Endpoint | Método | Auth | Descripción |
|---|---|---|---|
| `/kiosk` | GET | public | UI kiosko táctil |
| `/kiosk/create_order` | POST JSON | public | Crear orden + pago Flow |
| `/kiosk/payment_webhook` | POST | public | Confirmar pago |
| `/kiosk/return` | GET | public | Página post-pago |
| `/kiosk/order/<id>` | GET | public | Estado de orden |

---

## Acceso

- **Kiosk**: `https://food.ecocupon.cl/kiosk`
- **Admin Odoo**: `https://food.ecocupon.cl/web/login` (admin / admin123)
