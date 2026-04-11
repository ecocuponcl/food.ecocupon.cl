# DTC ENGINE - Motor de Diagnóstico Automotriz

## Estructura

```
dtc-engine/
├── dtc-database.sql      # Base de datos SQLite: códigos DTC → repuestos
├── dtc-gemma-prompt.txt  # Prompt especializado para IA Gemma
├── dtc-n8n-workflow.json # Flujo n8n completo (webhook → IA → Odoo → respuesta)
└── README.md             # Este archivo
```

## Arquitectura

```
APK/Telegram → Webhook n8n → Gemma IA → Base DTC → Odoo cotización → Respuesta
```

## Uso

### 1. Crear base de datos
```bash
sqlite3 dtc-engine.db < dtc-database.sql
```

### 2. Deploy en VPS
```bash
scp dtc-engine/dtc-database.sql root@89.116.23.167:/opt/smarterbot/dtc-engine/
scp dtc-engine/dtc-n8n-workflow.json root@89.116.23.167:/root/n8n-workflows/
```

### 3. Importar workflow en n8n
```bash
# Via API n8n
curl -X POST http://127.0.0.1:5678/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d @dtc-n8n-workflow.json
```

### 4. Probar
```bash
curl -X POST https://api.smarterbot.store/api/scan \
  -H "Content-Type: application/json" \
  -d '{
    "dtc_codes": ["P0300", "P0420"],
    "vehiculo": "Mazda 3 2018",
    "usuario": "+56979540471"
  }'
```

## Respuesta esperada

```json
{
  "diagnostico": {
    "P0300": {
      "problema": "Fallo de encendido aleatorio/múltiple cilindro",
      "gravedad": "alta",
      "repuestos": [
        {"nombre": "Bujías (set completo)", "precio": 35000, "prioridad": 1},
        {"nombre": "Bobinas de encendido", "precio": 85000, "prioridad": 2}
      ]
    },
    "P0420": {
      "problema": "Eficiencia del catalizador por debajo del umbral",
      "gravedad": "media",
      "repuestos": [...]
    }
  },
  "cotizacion": {
    "total_estimado": 120000,
    "odoo_quotation_id": 45,
    "link_pago": "https://odoo.ecocupon.cl/shop/payment/45"
  },
  "mensaje_usuario": "Detectamos 2 fallas en tu Mazda 3 2018...\n\nRecomendamos revisar:\n- Bujías (set completo) - $35.000\n- Bobinas de encendido - $85.000\n\nTotal estimado: $120.000\n\n¿Quieres comprar? https://odoo.ecocupon.cl/shop/payment/45"
}
```
