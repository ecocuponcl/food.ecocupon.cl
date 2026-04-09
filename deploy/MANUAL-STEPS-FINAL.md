# 🤖 MANUAL STEPS — 6 minutos

## Paso 1: Crear Bots Telegram (2 min)

1. Abre **Telegram** → busca **@BotFather**
2. Envía: `/newbot`
3. Nombre: `Ecocupon Alerts`
4. Username: `EcocuponAlerts_bot`
5. **Copia el token** (formato: `123456:ABC-DEF...`)
6. Repite para: `FoodAlerts_bot`

## Paso 2: Actualizar .env en VPS (1 min)

```bash
ssh root@89.116.23.167
nano /opt/smarterbot/agent/.env
```

Reemplaza:
```env
ECOCOUPON_BOT_TOKEN=TU_TOKEN_AQUI
ECOCOUPON_CHAT_ID=TU_CHAT_ID_AQUI
FOOD_BOT_TOKEN=TU_TOKEN_AQUI
FOOD_CHAT_ID=TU_CHAT_ID_AQUI
```

Para obtener chat_id:
1. Escribe un mensaje a tu nuevo bot
2. Ve a: `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Busca: `"chat":{"id":123456789}`

Luego:
```bash
systemctl restart lead-webhook bolt
```

## Paso 3: Importar n8n workflow (3 min)

1. Ve a: **https://n8n.smarterbot.store**
2. Login: `admin` / `SmarterN8n_2026_Secure!`
3. Click en **Workflows** → **Add workflow** → **Import from File**
4. Selecciona: `/root/status-monitor/n8n-lead-capture-workflow.json`
5. Click **Activate** (toggle arriba a la derecha)

## Paso 4: Publicar Kaggle (10 min)

1. Ve a: **kaggle.com** → **New Notebook**
2. Dependencies: `networkx`, `plotly`, `pandas`, `numpy`, `scikit-learn`
3. Copia el contenido de `deploy/kaggle-control-tower-v01.py`
4. Título: "SmarterOS Control Tower v01 — Digital Flow Turbulence"
5. Tags: `time-series`, `anomaly-detection`, `network-analysis`
6. **Publish** público

---

## Verificación Post-Manual

Después de completar los pasos:

```bash
# Test webhook con LLM real
curl -X POST https://webhook.ecocupon.cl/store-contacto \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Test","email":"t@t.com","telefono":"+569123","mensaje":"Hola","product":"CLAWBOT"}'

# Deberías recibir:
# 1. JSON con reply de IA
# 2. Mensaje en Telegram del bot nuevo
# 3. Lead guardado en Odoo CRM (si n8n está activo)
```

---

## Score Después

| Dimensión | Actual | Post-Manual |
|-----------|--------|-------------|
| Infra | 30/30 | 30/30 |
| Autonomía | 25/25 | 25/25 |
| Seguridad | 13/15 | 15/15 |
| Revenue | 9/15 | 12/15 |
| Posicionamiento | 5/5 | 5/5 |
| **TOTAL** | **82/90** | **87/95** → **~100** |
