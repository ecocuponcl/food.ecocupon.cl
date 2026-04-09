# 🤖 SMARTEROS MULTI-AGENT SYSTEM

## Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                      VOLT AGI                           │
│              (Central Coordinator)                      │
│                    port :9011                           │
└──────┬──────────┬──────────┬──────────┬────────────────┘
       │          │          │          │
  ┌────┴───┐ ┌────┴───┐ ┌───┴────┐ ┌───┴────┐
  │ Odoo   │ │ n8n    │ │ FastAPI│ │ Supab. │
  │ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │
  │ :9020  │ │ :9021  │ │ :9022  │ │ :9023  │
  └────────┘ └────────┘ └────────┘ └────────┘
```

## Cada Agente Especializado

| Agente | Monitorea | Auto-Repara | Reporta |
|--------|-----------|-------------|---------|
| **Odoo Agent** | DB, workers, modules | Restart, vacuum | Volt + Telegram |
| **n8n Agent** | Workflows, executions, creds | Restart, clean DB | Volt + Telegram |
| **FastAPI Agent** | Endpoints, latency, errors | Restart, clear cache | Volt + Telegram |
| **Supabase Agent** | API, tables, RLS, storage | Retry, backup | Volt + Telegram |

## Ciclo Diario

```
00:00 → Backup Supabase
06:00 → Health check completo
12:00 → Kaggle benchmarks sync
18:00 → Reporte diario a Volt
23:59 → Cleanup logs
```

## Reporte a Volt

Cada agente envía a `POST /api/agent/sync`:
```json
{
  "action": "daily_report",
  "agent": "odoo",
  "status": "healthy",
  "metrics": {...},
  "incidents": [...],
  "timestamp": "2026-04-09T18:00:00Z"
}
```

Volt consolida y envía resumen diario por Telegram.
