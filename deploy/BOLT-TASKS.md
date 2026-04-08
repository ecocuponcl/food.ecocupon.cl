# BOLT TASKS — Sprint 2026-04-08

## Tarea 1: Telegram Bot Token Fix
**Estado**: 🔴 Bloqueado
**Prioridad**: Crítica

### Problema
Token `8690191913:AAEHOJMxdUj2UBSwrPlpW0jZfMUDwpUNWc` es **InvalidToken**.
El servicio `ecocupon-telegram-bot` está en crash loop.

### Token Válido Disponible
```
7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc
```
Usado actualmente por `food-agent` container — **funcionando**.

### Acción Requerida
1. Opción A: Ir a @BotFather → `/mybots` → seleccionar bot de admin → copiar token nuevo
2. Opción B: Reutilizar el token de food-agent (pero evitar getUpdates conflict)
3. Actualizar:
   - `agent/telegram_bot.py` (default value)
   - `/opt/ecocupon/agent/.env` en VPS
   - `ecocupon-telegram-bot.service` Environment

### Verificación
```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getMe" | python3 -m json.tool
# Debe responder: {"ok":true,"result":{"id":...,"username":...}}
```

---

## Tarea 2: Deploy Kiosk Changes a VPS
**Estado**: 🟡 Pendiente
**Prioridad**: Alta

### Archivos modificados localmente
- `food_kiosk/static/src/js/kiosk.js` — QR scanner añadido
- `food_kiosk/views/food_kiosk_templates.xml` — UI scanner + QR display
- `food_kiosk/controllers/kiosk_controller.py` — QR generation post-pago
- `agent.py` — /recycle/validate mejorado + Telegram alerts

### Acción
```bash
# Copiar archivos modificados al container de Odoo
scp food_kiosk/static/src/js/kiosk.js root@89.116.23.167:/tmp/
scp food_kiosk/views/food_kiosk_templates.xml root@89.116.23.167:/tmp/

# O mejor: rebuild del container con nuevo volumen
docker cp /tmp/kiosk.js food-odoo:/mnt/extra-addons/food_kiosk/static/src/js/
docker restart food-odoo
```

### Verificación
1. Ir a `https://food.ecocupon.cl/en`
2. Ver botón "📷 Escanear QR de Envase"
3. Click → abre cámara → escanea QR → valida

---

## Tarea 3: SSL Cert agent.food.ecocupon.cl
**Estado**: 🟢 En progreso (auto-resuelve en 1-4h)
**Prioridad**: Media

### Problema
Cloudflare aún no provisionó certificado SSL para el subdominio nuevo.

### Acción
Esperar. Cloudflare auto-provisiona certs para dominios proxied.
Verificar cada 30 min:
```bash
curl -sI https://agent.food.ecocupon.cl/health
# Esperar: HTTP/2 200
```

### Workaround temporal
La landing puede llamar directo al IP:
```javascript
fetch('http://89.116.23.167:9001/decide', {...})
```

---

## Tarea 4: Token Cleanup
**Estado**: 🔴 Confuso
**Prioridad**: Alta

### Inventario Actual
| Token | Usado Por | Estado |
|-------|-----------|--------|
| `8690191913:AAEHO...` | ecocupon-telegram-bot, n8n, picoclaw | ❌ INVALID |
| `8690191913:AAEHO...-2UB...` | picoclaw (typo: dash vs colon) | ❌ INVALID |
| `7631713367:AAFCRv...` | food-agent container | ✅ VÁLIDO |
| `7631713367:AAE62f...` | smarter-telegram-bot | ⚠️ CONFLICT |

### Acción
1. Identificar qué bot es cuál (BotFather → `/mybots`)
2. Asignar tokens únicos por servicio
3. Eliminar referencias al token inválido `8690191913:...`
4. Crear tabla de asignación:

```
food-agent        → 7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc
smarter-telegram  → 7631713367:AAE62f-N1aQOzVvdnHNvbKdrJ15Q2FrTZHg
ecocupon-admin    → [CREAR NUEVO]
picoclaw-alerts   → [CREAR NUEVO]
n8n-notifications → [REUSAR food-agent O CREAR NUEVO]
```

---

## Tarea 5: Score del Sprint
**Estado**: ⏳ Post-sprint

### Métricas a Reportar
| KPI | Antes | Después | Score |
|-----|-------|---------|-------|
| Uptime | ? | ? | /30 |
| Response time | ? | ? | /20 |
| Conversión | 0% | ? | /25 |
| Error rate | ? | ? | /15 |
| Alertas < 60s | ? | ? | /10 |
| **TOTAL** | | | **/100** |

### Criterios de Éxito
- Score > 80: Sprint exitoso
- Score 60-80: Mejorable
- Score < 60: Re-planificar

---

## Lecciones para Próximo Sprint
*(Completar al final)*

1. 
2. 
3. 
