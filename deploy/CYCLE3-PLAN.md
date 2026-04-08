# 🟡⚫ PLAN — Ciclo 3: Agente Local Autónomo

## 📊 Estado Actual (Audit 2026-04-08 13:55 UTC)

### ✅ Operativo
| Componente | Estado | Detalle |
|------------|--------|---------|
| status-monitor.timer | ✅ Cada 60s | Checkea 10 servicios |
| alert-checker.timer | ✅ Cada 60s | Evalúa alertas + Telegram |
| auto-recovery.py | ✅ Activo | 4+ recovery ejecutados |
| status-aggregator :8002 | ✅ Activo | /status.json público |
| n8n auth | ✅ Protegido | Basic auth activado |
| Caddy DB block | ✅ 403 | /web/database/* bloqueado |
| Supabase logs | ✅ Registrando | service_status_logs |

### ⚠️ Mejorable
| Problema | Impacto | Solución |
|----------|---------|----------|
| **Duplicación**: status-monitor + status-aggregator | Recursos desperdiciados | Unificar en 1 solo proceso |
| **status-aggregator en auto-restart** | Crash loop posible | Debug + fix |
| **Caddy down en monitor pero ok en aggregator** | Inconsistencia de checks | Unificar método de check |
| **No hay Supabase service_role key** | No puede loggear | Usar API key del .env |

---

## 🎯 OPTIMIZACIÓN — Unificar en 1 Agente

### Arquitectura Propuesta

```
┌─────────────────────────────────────────────┐
│         AGENTE LOCAL (1 proceso)             │
│         /opt/ecocupon/agent-local/           │
│                                              │
│  main.py — FastAPI :8002                     │
│  ├── GET /status.json   → checkea servicios  │
│  ├── GET /recovery.json → log de acciones    │
│  ├── GET /health        → health propio      │
│  │                                           │
│  background_loop (cada 60s):                 │
│  ├── check_all_services()                    │
│  ├── log_to_supabase()                       │
│  ├── if down → auto_recovery()               │
│  ├── if down → alert_telegram()              │
│  └── cache status.json                       │
└─────────────────────────────────────────────┘
```

### Lo que se elimina (redundante)
| Archivo | Razón |
|---------|-------|
| `/root/status-monitor/main.py` | Se fusiona en agent-local |
| `/root/status-monitor/alert-workflow.py` | Se fusiona en agent-local |
| `/opt/ecocupon/status-aggregator/` | Se fusiona en agent-local |
| `status-monitor.timer` | Reemplazado por loop interno |
| `alert-checker.timer` | Reemplazado por loop interno |
| `status-aggregator.service` | Reemplazado por agent-local.service |

### Lo que se mantiene
| Archivo | Razón |
|---------|-------|
| `/root/status-monitor/recovery-rules.json` | Reglas de recovery bien definidas |
| `/root/status-monitor/recovery-actions.json` | Log de acciones |
| `auto-recovery.py` | Se importa como módulo |

---

## 📋 PLAN DE EJECUCIÓN

### Fase 1: Crear Agente Unificado (10 min)
- Crear `/opt/ecocupon/agent-local/main.py`
- Fusionar: status check + auto recovery + alertas + API
- FastAPI :8002 con /status.json, /recovery.json, /health
- Background loop cada 60s

### Fase 2: Systemd Service (2 min)
- Crear `agent-local.service`
- Reemplazar: status-monitor.timer + alert-checker.timer + status-aggregator.service
- 1 solo servicio en vez de 3

### Fase 3: Cleanup (5 min)
- Stop timers redundantes
- Limpiar archivos duplicados
- Mantener recovery-rules.json y recovery-actions.json

### Fase 4: Verificación (3 min)
- `curl https://os.smarterbot.store/status.json`
- `curl https://os.smarterbot.store/recovery.json`
- Verificar auto-recovery funciona
- Verificar alertas Telegram

---

## 📊 Score Proyectado

| Dimensión | Actual | Después | Δ |
|-----------|--------|---------|---|
| Uptime (30%) | 28 | **30** | +2 (1 proceso vs 3) |
| Latencia (20%) | 17 | **19** | +2 (sin overhead timers) |
| Conversión (25%) | 0 | **0** | Sin cambio |
| Error Rate (15%) | 13 | **15** | +2 (menos puntos de fallo) |
| Alertas (10%) | 8 | **10** | +2 (integrado) |
| **TOTAL** | **66** | **74** | **+8** |

---

## 🔧 Archivos a Crear

```
/opt/ecocupon/agent-local/
├── main.py              # Agente unificado (FastAPI + loop + recovery)
├── recovery_rules.json  # Copia de /root/status-monitor/recovery-rules.json
└── recovery_log.json    # Copia de /root/status-monitor/recovery-actions.json

/etc/systemd/system/
└── agent-local.service  # 1 servicio reemplaza 3
```

---

## ⏭️ Post-Optimización

1. **Supabase SQL** — Ejecutar `deploy/supabase-schema-complete.sql` (requiere acceso dashboard)
2. **Telegram bot** — Crear token nuevo (@BotFather) para reemplazar 8690191913 (inválido)
3. **n8n workflow** — Importar `80-status-aggregator.json` (requiere login n8n)
4. **Deploy kiosk** — `docker restart food-odoo` con QR scanner
5. **Primer scan real** → métrica de conversión
