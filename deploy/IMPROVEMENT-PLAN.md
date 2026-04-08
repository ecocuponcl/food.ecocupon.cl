# PLAN DE MEJORA — Seguridad + Observabilidad
# Ciclo: 2026-04-08 | Sprint 1

## 🟡⚫ PRINCIPIO
```
STATUS REAL = BACKEND AGGREGADO
FRONTEND = SOLO VISUAL
ODOO = ERP por TENANT_ID (nunca expuesto)
n8n = Motor de reglas (autenticado)
```

---

## 🔴 FASE 1: FIX CRÍTICOS (HOY)

### 1.1 Odoo19 Database Selector — CERRAR
**Problema**: `/web/database/selector` público, sin master password
**Impacto**: Cualquiera puede crear, duplicar o borrar la DB

**Fix**:
```bash
# A. Agregar ADMIN_PASSWORD al docker-compose
# /root/odoo19/docker-compose.yml
environment:
  - ADMIN_PASSWORD=Odoo19_Master_v+LrCj3ZdOF4

# B. Desactivar list_db
# /etc/odoo/odoo.conf (dentro del container)
list_db = False
dbfilter = ^smarter_.*$

# C. Bloquear ruta en Caddy (si no se necesita database manager)
# /etc/caddy/Caddyfile
erp.smarterbot.store {
    @dbmanager path /web/database/*
    respond @dbmanager 403
    reverse_proxy http://127.0.0.1:8069
}
```

### 1.2 n8n Authentication — ACTIVAR
**Problema**: n8n sin usuario, workflows editables por cualquiera
**Impacto**: Pueden modificar flujos de pago, ver API keys

**Fix**:
```bash
# /root/n8n/.env o docker-compose
N8N_USER_MANAGEMENT_ENABLED=true
N8N_SECURE_COOKIE=true
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=$(openssl rand -base64 32)
```

### 1.3 Limpiar Secrets Expuestos
**Problema**: Mailgun, Telegram, OpenRouter en `docker exec env`

**Fix**:
```bash
# Mover secrets a Docker secrets o archivo .env restringido
chmod 600 /root/n8n/.env
chown root:root /root/n8n/.env

# Rotar tokens expuestos (especialmente Mailgun y Telegram)
```

---

## 🟡 FASE 2: OBSERVABILIDAD CENTRALIZADA

### 2.1 Endpoint /status.json (n8n webhook)
**Principio**: Frontend SOLO consulta 1 endpoint

**Arquitectura**:
```
browser → os.smarterbot.store/status.json
                              ↓
                    n8n webhook (cron 60s)
                    ↓    ↓    ↓    ↓
                  LLM   QR   n8n  Odoo
                    ↓    ↓    ↓    ↓
              Supabase: service_status_logs
```

**Workflow n8n**:
1. Trigger: Schedule cada 60s
2. HTTP Request → cada servicio health endpoint
3. Mide latencia (Response Time)
4. Escribe en Supabase: `service_status_logs`
5. IF status != ok → Telegram alerta
6. HTTP Response → JSON limpio

**Output JSON**:
```json
{
  "status": "ok",
  "services": {
    "llm":   {"status": "ok", "latency": 120, "model": "cloudflare_ai"},
    "qr":    {"status": "ok", "latency": 80,  "tokens": 15},
    "n8n":   {"status": "ok", "latency": 200, "workflows": 2},
    "odoo":  {"status": "ok", "latency": 300, "tenant": "food_kiosk"},
    "agent": {"status": "ok", "latency": 50,  "verticals": 3},
    "bolt":  {"status": "ok", "latency": 150, "metrics": 42},
    "db":    {"status": "ok", "latency": 5,   "connections": 12},
    "redis": {"status": "ok", "latency": 2,   "memory": "15MB"},
    "caddy": {"status": "ok", "latency": 10,  "routes": 30}
  },
  "timestamp": "2026-04-08T12:00:00Z"
}
```

### 2.2 Supabase Schema — service_status_logs
```sql
CREATE TABLE IF NOT EXISTS service_status_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service     TEXT NOT NULL,
    status      TEXT NOT NULL,  -- 'ok', 'degraded', 'down'
    latency_ms  INT NOT NULL DEFAULT 0,
    details     JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- Índice para queries rápidos
CREATE INDEX idx_status_logs_service_time 
    ON service_status_logs(service, created_at DESC);

-- Retención automática (retener 30 días)
CREATE OR REPLACE FUNCTION cleanup_old_status_logs()
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM service_status_logs 
    WHERE created_at < now() - interval '30 days';
END;
$$;
```

### 2.3 Frontend OS Portal — Cambiar a 1 endpoint
**Antes**:
```js
// 10 llamadas directas desde browser (INSEGURO)
fetch('https://llm.smarterbot.store/health')
fetch('https://n8n.smarterbot.store/healthz')
// ... etc
```

**Después**:
```js
// 1 llamada centralizada
const res = await fetch('/status.json');
const data = await res.json();
renderServiceCards(data.services);
```

---

## 🟢 FASE 3: REGLAS POR TENANT_ID

### 3.1 Principio
```
Cada tenant tiene sus propias reglas de negocio
Odoo ERP NO expone datos cruzados entre tenants
n8n filtra por tenant_id en todos los workflows
```

### 3.2 Tabla Supabase: tenant_policies
```sql
CREATE TABLE tenant_policies (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   TEXT NOT NULL UNIQUE,
    rules       JSONB NOT NULL,  -- 50 reglas por tenant
    active      BOOLEAN DEFAULT true,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);
```

### 3.3 Estructura de 50 Reglas (por Tenant)
```yaml
# tenant: ecocupon_cl
rules:
  # Precios
  price_warn_mult: 3.0      # Alerta si precio > 3x referencia
  price_reject_mult: 10.0   # Rechaza si precio > 10x referencia
  min_price: 10             # Precio mínimo CLP
  max_price: 1000000        # Precio máximo CLP
  
  # Reciclaje
  recycle_min_weight: 0.5   # Peso mínimo kg
  recycle_max_daily: 50     # Máximo reciclajes/día por usuario
  cashback_rate_vidrio: 300 # CLP/kg
  cashback_rate_carton: 200 # CLP/kg
  cashback_rate_pet: 500    # CLP/kg
  cashback_rate_lata: 60    # CLP/kg
  
  # Fraude
  fraud_max_scans_per_hour: 10
  fraud_same_ip_window: 60  # segundos
  fraud_geo_radius_km: 5    # distancia máxima entre scans
  fraud_score_threshold: 0.7
  
  # Reputación
  reputation_initial: 1.0
  reputation_min: 0.1
  reputation_max: 2.0
  reputation_sandbox_penalty: 0.8
  
  # Alertas
  alert_reject_rate: 0.25        # 25% rechazo = alerta
  alert_sandbox_rate: 0.35       # 35% sandbox = alerta
  alert_avg_score_min: 6.5       # Score promedio mínimo
  
  # Pagos
  payment_timeout: 300           # 5 min
  payment_max_daily: 1000000     # CLP
  payment_min_withdraw: 5000     # CLP
  
  # API
  api_rate_limit: 100            # req/min
  api_burst_limit: 20            # req/segundo
  
  # QR
  qr_ttl_hours: 24              # Expiración QR
  qr_max_per_user_daily: 20
  qr_min_cashback: 50           # CLP mínimo por QR
  
  # ... hasta 50 reglas
```

### 3.4 n8n Workflow: Tenant Rule Engine
```
Trigger: HTTP Webhook (cada validate/scan/decision)
  ↓
Extract: tenant_id from payload
  ↓
Fetch: tenant_policies WHERE tenant_id = ?
  ↓
Apply: rules to current operation
  ↓
IF violation → reject + log + alert
IF ok → proceed + log
  ↓
Response: {status, applied_rules, violations[]}
```

---

## 🔁 CICLO DE MEJORA CONTINUA

```
┌─────────────────────────────────────────┐
│          CICLO VIRTUOSO                 │
│                                         │
│  1. MONITOREAR → n8n cron 60s           │
│       ↓                                 │
│  2. DETECTAR → status != ok             │
│       ↓                                 │
│  3. ALERTAR → Telegram < 30s            │
│       ↓                                 │
│  4. DIAGNOSTICAR → Bolt analiza logs    │
│       ↓                                 │
│  5. FIX → Aplica corrección             │
│       ↓                                 │
│  6. VERIFICAR → Re-check 60s            │
│       ↓                                 │
│  7. APRENDER → Actualiza OPENSPEC       │
│       ↓                                 │
│  8. SCORE → Actualiza métricas          │
│       ↓                                 │
│  → REPETIR (cada ciclo mejora score)    │
└─────────────────────────────────────────┘
```

### Scoring por Ciclo
| Dimensión | Peso | Meta | Fórmula |
|-----------|------|------|---------|
| Uptime | 30% | >99% | `sum(ok_checks) / total_checks` |
| Latencia | 20% | <200ms | `avg(latency_ms) across services` |
| Conversión | 25% | >80% | `completed_funnels / started_funnels` |
| Error Rate | 15% | <1% | `errors / total_requests` |
| Alertas | 10% | <60s | `avg(alert_response_time)` |

---

## 📋 DELEGACIÓN DE TAREAS

### Bolt (Gerente IA)
| Tarea | Descripción | Criterio Éxito |
|-------|-------------|----------------|
| B1 | Crear workflow n8n status.json | Endpoint responde en <500ms |
| B2 | Crear tabla service_status_logs | Schema aplicado en Supabase |
| B3 | Actualizar OS portal a 1 endpoint | Frontend usa solo /status.json |
| B4 | Crear tabla tenant_policies | 50 reglas seed para ecocupon_cl |
| B5 | Workflow n8n tenant rule engine | Filtra por tenant_id en cada request |

### Picoclaw (Monitor Autónomo)
| Tarea | Descripción | Criterio Éxito |
|-------|-------------|----------------|
| P1 | Check status.json cada 60s | Reporta si status != ok |
| P2 | Alerta Telegram si DOWN | <30s detección → notificación |
| P3 | Log hourly score | Escribe score en Supabase |

### Humano (Tú)
| Tarea | Descripción | Urgencia |
|-------|-------------|----------|
| H1 | Rotar secrets expuestos en n8n | 🔴 Inmediata |
| H2 | Activar auth en n8n | 🔴 Inmediata |
| H3 | Bloquear /web/database/selector | 🔴 Inmediata |
| H4 | Rotar token Telegram 8690191913 | 🟡 Esta semana |
| H5 | Revisar y aprobar 50 reglas tenant | 🟡 Esta semana |

---

## 📊 ESTADO ACTUAL vs META

| Capa | Actual | Meta | Gap |
|------|--------|------|-----|
| Portal OS | ✅ Visual | ✅ Centralizado | Frontend → 1 endpoint |
| Servicios | ✅ Vivos | ✅ Monitoreados | status.json |
| Odoo ERP | 🔴 Expuesto | 🔒 Tenant-isolated | Auth + dbfilter |
| n8n | 🔴 Sin auth | 🔒 Autenticado | User management |
| Observabilidad | ⚠️ Parcial | ✅ Completa | Logs + alertas |
| Reglas | ⚠️ 2 archivos YAML | ✅ 50 reglas/tenant | DB-driven |
| Alertas | ⚠️ Parciales | ✅ <30s | n8n → Telegram |

---

## ✅ CHECKLIST POST-SPRINT

```
[ ] 1.1 Odoo19 database selector cerrado
[ ] 1.2 n8n authentication activada
[ ] 1.3 Secrets expuestos rotados
[ ] 2.1 Endpoint /status.json funcionando
[ ] 2.2 service_status_logs creada en Supabase
[ ] 2.3 OS portal usa solo 1 endpoint
[ ] 3.1 tenant_policies creada
[ ] 3.2 50 reglas seed para ecocupon_cl
[ ] 3.3 n8n tenant rule engine operativo
[ ] 4.1 Picoclaw monitorea status.json
[ ] 4.2 Alertas Telegram <30s
[ ] 4.3 Score first cycle > 60/100
```
