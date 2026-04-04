# 🍔 Ecocupon Payment Agent

FastAPI agent que conecta el kiosco Odoo con Flow.cl para procesar pagos.

## Setup

```bash
# 1. Copiar variables
cp .env.example .env

# 2. Editar .env con tu API key de Flow
nano .env

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Correr
uvicorn agent:app --reload --port 9000
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/create_payment` | Crear pago en Flow |
| POST | `/webhook/flow` | Recibir callbacks de Flow |

## Create Payment

```bash
curl -X POST http://localhost:9000/create_payment \
  -H "Content-Type: application/json" \
  -d '{"amount": 9990, "order_id": 1}'
```

Response:
```json
{
  "url": "https://www.flow.cl/v2/normal/payment?token=xxx",
  "token": "xxx"
}
```

## Arquitectura

```
Odoo (VPS) → POST /create_payment → Agent (Mac) → Flow API
```
