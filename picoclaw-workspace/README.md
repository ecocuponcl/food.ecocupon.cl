# 🤖 PicoClaw — Guía de Tareas Prolongadas y Monitoreo Autónomo

## Arquitectura de Tareas de Larga Duración

PicoClaw tiene **3 mecanismos** para trabajar de forma autónoma y prolongada:

---

### 1️⃣ **CRON Jobs** (Programados)

**Qué es:** Jobs persistentes que sobreviven restarts, ejecutados por el gateway.

**Tipos de Schedule:**
| Tipo | Ejemplo | Uso |
|------|---------|-----|
| `cron_expr` | `0 */4 * * *` | Cada 4 horas |
| `every_seconds` | `3600` | Cada 1 hora |
| `at_seconds` | `86400` | Una vez en 24h |

**Modos de Ejecución:**
| Modo | Descripción | Ejemplo |
|------|-------------|---------|
| `command` | Ejecuta shell command → output al agent | Auditoría Caddy |
| `agent` | Pasa mensaje al LLM → usa herramientas | Health check inteligente |
| `deliver` | Envía mensaje directo al canal (sin LLM) | Reminder simple |

**Config actual (3 jobs):**
```json
{
  "caddy-audit-4h": "0 */4 * * *",    // Auditoría Caddy cada 4h
  "ssl-check-daily": "0 9 * * *",     // Check SSL diario 9AM
  "health-check-30m": "*/30 * * * *"  // Health check servicios 30min
}
```

**Timeout:** `exec_timeout_minutes: 0` = **sin límite** (infinite)

---

### 2️⃣ **Spawn Tool** (Sub-agentes en Background)

**Qué es:** Delega tareas pesadas a sub-agentes independientes que corren en paralelo.

**Cuándo usar spawn:**
- Tareas que toman > 60 segundos
- Browser automation (Playwright, scraping)
- Procesamiento de archivos grandes
- Múltiples tareas independientes en paralelo

**Cómo funciona:**
```
User: "revisa todos los dominios de Cloudflare y genera un reporte completo"
         ↓
PicoClaw → spawn("domain audit subagent")
         ↓
   ┌─────────────────┐
   │ Sub-agent #1    │ → Escanea zonas Cloudflare
   │ (independiente) │ → Check SSL cada dominio
   │                 │ → Genera JSON report
   └────────┬────────┘
            ↓ MessageBus
   PicoClaw → Telegram: "✅ Audit completo: 15 domains, 2 warnings"
```

**Config:**
```json
"spawn": {
    "enabled": true,
    "max_concurrent": 3,    // Hasta 3 sub-agentes en paralelo
    "timeout_minutes": 30   // Timeout por sub-agente
}
```

---

### 3️⃣ **Hooks** (Event-driven Automation)

**Qué es:** Triggers automáticos en eventos del sistema.

**Hooks configurados:**
| Evento | Trigger | Acción |
|--------|---------|--------|
| `on_startup` | PicoClaw inicia | Telegram: "🚀 Started. Model: X, Jobs: Y" |
| `on_cron_fail` | Job falla | Telegram: "⚠️ Job X failed: error" |

---

## 📊 Monitoreo de Dominios — Implementación Actual

### Skills Instalados en VPS

```
/root/.picoclaw/workspace/
├── scripts/
│   ├── caddy-audit.sh      # Auditoría Caddyfile (fast, < 30s)
│   └── cf-domain-scan.sh   # Escaneo Cloudflare zones
├── skills/
│   ├── domain-monitor/
│   │   └── SKILL.md        # Instrucciones para el agent
│   └── caddy-audit/
│       └── SKILL.md        # Instrucciones auditoría Caddy
└── cron/
    └── (jobs.json auto-managed by PicoClaw)
```

### Qué Monitorea

| Check | Frecuencia | Método | Alerta |
|-------|-----------|--------|--------|
| **HTTP status** | Cada 4h | `curl --max-time 5` | Telegram si 5xx o timeout |
| **SSL expiry** | Diario 9AM | `openssl s_client` | Telegram si < 7 días |
| **Service health** | Cada 30min | `/health` endpoints | Telegram si down |
| **Caddy config** | Cada 4h | Parse Caddyfile | Reporte de cambios |
| **Cloudflare zones** | Manual | API Cloudflare | Reporte completo |

### Dominios Monitoreados (13 total)

| Dominio | Status | HTTP | Notas |
|---------|--------|------|-------|
| ecocupon.cl | ✅ | 200 | Landing |
| agent.food.ecocupon.cl | ✅ | 200 | EcoCupon Agent API |
| n8n.smarterbot.cl | ✅ | 200 | n8n automation |
| n8n.smarterbot.store | ✅ | 200 | n8n instance 2 |
| bolt.smarterbot.store | ✅ | 200 | Bolt dashboard |
| dokploy.smarterbot.store | ✅ | 200 | Dokploy panel |
| docs.smarterbot.cl | ✅ | 200 | SmarterOS docs |
| erp.smarterbot.cl | ✅ | 200 | Odoo ERP |
| food.smarterbot.cl | ✅ | 200 | Smarter food API |
| ai.smarterbot.cl | ✅ | 200 | Cloudflare AI Agent |
| **food.ecocupon.cl** | ⚠️ | **502** | **Odoo backend down** |
| **docling.smarterbot.store** | ⚠️ | **502** | **Docling service down** |
| **llm.smarterbot.store** | ⚠️ | **500** | **SmarterOS API error** |

---

## 🔧 Optimizaciones Aplicadas

### Antes vs Después

| Parámetro | Antes | Después | Impacto |
|-----------|-------|---------|---------|
| `max_tool_iterations` | 10 | **20** | Permite tareas más complejas |
| `request_timeout` | 120s | **180s** | Soporta APIs lentas |
| `exec_timeout_minutes` | 5 | **0 (infinite)** | Tareas largas sin timeout |
| `max_tokens` | 2048 | **4096** | Respuestas más completas |
| `spawn.enabled` | ❌ | **✅** | Sub-agentes en background |
| `spawn.max_concurrent` | N/A | **3** | 3 tareas paralelas |
| `cron jobs` | 0 | **3** | Monitoreo automático |
| `hooks` | 0 | **2** | Alertas automáticas |
| `exec.allowed_commands` | N/A | **whitelist** | Seguridad + flexibilidad |
| `http.allowed_hosts` | 3 | **10** | Acceso a todos los servicios |

### Flujo de Monitoreo Autónomo

```
┌─────────────────────────────────────────────────────────────┐
│                    CRON SCHEDULE                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  00:00 ── Health Check (agent)                              │
│           ↓                                                 │
│           curl /health de todos los servicios               │
│           ↓                                                 │
│           Si algún service down → Telegram alert            │
│                                                             │
│  04:00 ── Caddy Audit (command)                             │
│           ↓                                                 │
│           bash caddy-audit.sh                               │
│           ↓                                                 │
│           Parsea Caddyfile → curl cada dominio              │
│           ↓                                                 │
│           Reporte JSON → agent loop → Telegram si issues    │
│                                                             │
│  08:00 ── Health Check                                     │
│  09:00 ── SSL Check (command)                               │
│           ↓                                                 │
│           openssl s_client cada dominio                     │
│           ↓                                                 │
│           Si SSL expira < 7d → Telegram + auto-renew        │
│                                                             │
│  12:00 ── Caddy Audit                                      │
│  12:30 ── Health Check                                     │
│  16:00 ── Caddy Audit                                      │
│  20:00 ── Caddy Audit                                      │
│  20:30 ── Health Check                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 💰 Costo de Ejecución

| Componente | RAM | CPU | Costo/hora |
|------------|-----|-----|------------|
| PicoClaw gateway | ~15MB | <1% | $0.001 |
| Cron jobs (3) | burst only | burst only | $0.005 |
| Spawn (max 3) | ~50MB c/u | variable | $0.01 |
| **Total 24/7** | **<100MB** | **<5%** | **~$0.15/día** |

---

## 📱 Comandos por Telegram

Puedes pedirle a PicoClaw por Telegram:

| Comando | Acción |
|---------|--------|
| `revisa dominios` | Ejecuta caddy-audit.sh ahora |
| `status servicios` | Health check manual |
| `escanea cloudflare` | Full Cloudflare zone scan |
| `check ssl food.ecocupon.cl` | SSL cert detail |
| `restart caddy` | `systemctl restart caddy` |
| `logs picoclaw` | Últimos 50 lines del log |

---

## 🚨 Alertas Automáticas

PicoClaw enviará Telegram automáticamente cuando:

1. **Dominio no responde** (HTTP 000) → "🚨 CRITICAL: domain.com not responding"
2. **Backend error** (HTTP 5xx) → "⚠️ WARNING: domain.com HTTP 502"
3. **SSL expira < 7 días** → "🔒 SSL expiring in X days: domain.com"
4. **Cron job falla** → "⚠️ Cron job 'caddy-audit-4h' failed: error"
5. **PicoClaw se reinicia** → "🚀 PicoClaw started. Model: openrouter. Jobs: 3."

---

## 🔮 Próximos Pasos (Opcional)

- [ ] Conectar AnythingLLM como LLM local (requiere API token)
- [ ] Agregar Cloudflare API token para escaneo automático de zones
- [ ] Integrar con n8n webhook para logging en PostgreSQL
- [ ] Agregar auto-remediation (restart services cuando caen)
- [ ] Dashboard Bolt con métricas de uptime
