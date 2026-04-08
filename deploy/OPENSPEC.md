# EcoCupon OpenSpec — Bolt AI Manager

## 🏗️ Arquitectura del Ciclo Virtuoso

```
┌─────────────────────────────────────────────────────────┐
│                    BOLT AI MANAGER                       │
│  (Gerente IA con acceso a smarterMCP + LLM + Telegram)  │
└──────────────────────┬──────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          │            │            │
     📊 Monitor    🔧 Fix       📈 Mejora
          │            │            │
    ┌─────┴─────┐ ┌───┴───┐  ┌─────┴─────┐
    │ Bolt Dash │ │ Caddy │  │ OpenSpec  │
    │ Picoclaw  │ │ Agent │  │ Contracts │
    │ n8n       │ │ Odoo  │  │ Scoring   │
    └───────────┘ └───────┘  └───────────┘
```

## 📐 Dimensiones

### LOCAL (desarrollo)
- Código fuente: `/Users/mac/dev/2026/food.ecocupon.cl/`
- Git repo: `main` branch
- Framework: Odoo 19 + FastAPI + Streamlit
- Testing: `python3 -m py_compile` + curl

### VPS (producción)
- IP: `89.116.23.167`
- 23 containers Docker
- Caddy reverse proxy (23 dominios)
- Systemd services (bot, monitoring)

### MÓVIL (usuario final)
- QR Scanner: kiosk → cámara → `/recycle/validate`
- Telegram Bot: comandos admin remotos
- MiniApp: `app.ecocupon.cl/miniapp`

## 🎯 Contratos de Servicio

### Contrato 1: QR Funnel
```
ENTRADA: QR token string
PROCESO: POST /recycle/validate {qr_code: "..."}
SALIDA: {valid: bool, material: str, weight: float, cashback: int}
SLA: < 200ms response time
ALERT: Telegram si validación exitosa
```

### Contrato 2: Payment Flow
```
ENTRADA: Cart items + Flow.cl payment
PROCESO: /create_payment → webhook confirmation
SALIDA: QR codes generados + cashback acreditado
SLA: < 5s end-to-end
ALERT: Telegram si pago confirmado
```

### Contrato 3: Health Monitoring
```
CHECK: Cada 30 min (Picoclaw cron)
SERVICES: Odoo, Agent, n8n, Caddy, Postgres, Redis
SALIDA: Reporte Telegram si algo DOWN
SLA: < 60s detección → alerta
```

## 📊 Scoring del Ciclo de Mejora

| Dimensión | Métrica | Meta | Peso |
|-----------|---------|------|------|
| Disponibilidad | Uptime % | > 99% | 30% |
| Velocidad | Response time | < 200ms | 20% |
| Conversión | QR scans → cashback | > 80% | 25% |
| Calidad | Error rate | < 1% | 15% |
| Alertas | Detección → notificación | < 60s | 10% |

## 🔧 Tareas Delegables a Bolt

### Tarea A: Fix Telegram Bot Token
- **Problema**: Token `8690191913:...` es InvalidToken
- **Acción**: Crear nuevo bot via BotFather → actualizar `.env`
- **Files**: `agent/telegram_bot.py`, systemd service

### Tarea B: Deploy Código Local → VPS
- **Problema**: 4 archivos modificados sin commitear
- **Acción**: Sync `food_kiosk/` changes a Odoo container
- **Files**: `kiosk.js`, `food_kiosk_templates.xml`, `kiosk_controller.py`

### Tarea C: SSL Cert agent.food.ecocupon.cl
- **Problema**: Handshake failure (cert no provisionado)
- **Acción**: Esperar auto-provision de Cloudflare (1-4h)
- **Verify**: `curl -sI https://agent.food.ecocupon.cl/health`

### Tarea D: Alinear Local vs VPS Agent
- **Problema**: Local `agent.py` (909 líneas) ≠ VPS container (80 líneas)
- **Acción**: Decidir cuál es source of truth, sincronizar
- **Files**: `agent.py` vs `food-agent` container

### Tarea E: Bot Token Cleanup
- **Problema**: 4 procesos compitiendo por 3 tokens
- **Acción**: Definir quién usa qué token
- **Tokens válidos**: `7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc` (food-agent)

## 📋 Checklist de Verificación Post-Deploy

```
[ ] food.ecocupon.cl/en → 200 OK
[ ] agent.food.ecocupon.cl/health → 200 JSON
[ ] qr.ecocupon.cl → 200 HTML
[ ] /recycle/validate → responde con JSON
[ ] QR scanner en kiosk → cámara activa
[ ] Telegram bot /start → responde
[ ] Telegram bot /status → muestra servicios
[ ] Bolt dashboard → métricas en vivo
[ ] Picoclaw cron → funnel check 30m
```

## 🔄 Ciclo de Mejora Continua

```
1. MONITOREAR → Picoclaw chequea cada 30m
2. DETECTAR → Si algo falla, alerta Telegram
3. DIAGNOSTICAR → Bolt analiza logs y métricas
4. FIX → Bolt aplica corrección o delega
5. VERIFICAR → Re-check post-fix
6. APRENDER → Actualizar OpenSpec con lección
7. REPETIR → Score sube con cada ciclo
```

## 🤖 SmarterMCP Integration Points

| MCP Server | Función | Endpoint |
|------------|---------|----------|
| n8n-mcp | Trigger workflows | `http://localhost:8090` |
| Caddy MCP | Config routes | `/etc/caddy/Caddyfile` |
| Docker MCP | Manage containers | Docker socket |
| Supabase MCP | Query DB | `rjfcmmzjlguiititkmyh.supabase.co` |

## 📝 Lecciones Aprendidas

1. **Token Cloudflare DNS:Edit ≠ Cache Purge** — necesita permisos separados
2. **Cloudflare cache de Vercel persiste** — aunque DNS cambie, purge manual necesario
3. **Telegram bot token InvalidToken** — `8690191913:...` revocado, usar `7631713367:...`
4. **Local ≠ VPS code** — sync manual necesario, no auto-deploy
5. **Caddy route nuevo → SSL cert tarda 1-4h** — Cloudflare universal SSL
6. **Picoclaw cron jobs necesitan `allowed_commands`** — sinón wildcard para scripts custom
7. **Python PEP 668 bloquea pip system-wide** — necesita `--break-system-packages` o venv
