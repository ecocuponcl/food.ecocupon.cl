# 🚀 SMARTEROS v4 — EXECUTION PLAN

## ORDEN LÓGICO (prioridad → impacto)

```
1. Control Tower UI        → Base visual para todo
2. Email Scraping Pipeline → Leads inbound automáticos
3. Auto-Facturación Odoo   → Cierra ventas sin intervención
4. Web Scraping            → Leads outbound proactivos
```

## TIMELINE ESTIMADO

| Fase | Tarea | Tiempo | Complejidad |
|------|-------|--------|-------------|
| **1** | Control Tower UI | 30 min | Media |
| **2** | Email Scraping (n8n) | 20 min | Baja |
| **3** | Odoo Auto-Invoice | 25 min | Media |
| **4** | Web Scraping | 40 min | Alta |

---

## FASE 1: Control Tower UI

### Qué es
Panel web que muestra en tiempo real:
- Balance del sistema (Yin/Yang gauge)
- Leads activos con scoring
- Revenue actions en vivo
- HOT lead alerts
- Service health status
- Mobile engagement tracking

### Stack
- HTML/CSS/JS vanilla (fast, no framework)
- Fetch desde /status.json, /balance.json, /revenue.json
- Auto-refresh cada 15s
- Dark theme (🟡⚫)

### Deploy
- `/var/www/control-tower/index.html`
- Caddy route: `so.smarterbot.store` → `/var/www/control-tower`

---

## FASE 2: Email Scraping Pipeline

### Qué es
n8n lee emails entrantes → LLM califica intención → Si lead → auto-add a pipeline

### Stack
- n8n IMAP trigger (cada 5 min)
- LLM intent analysis (via llm.smarterbot.store)
- Webhook POST a lead-webhook (:8004)
- Auto-export a Kaggle (existing cron)

### Deploy
- Workflow JSON → n8n import
- IMAP credentials en n8n
- Webhook endpoint ya existe

---

## FASE 3: Auto-Facturación Odoo

### Qué es
Cuando lead convierte (score > 85 + mobile_engaged):
- Crea factura en Odoo automáticamente
- Envía email con factura
- Actualiza Trello card
- Notifica Telegram

### Stack
- Odoo XML-RPC API
- Revenue engine trigger (score + status change)
- n8n workflow para email
- Telegram alert existing

### Deploy
- Script Python en VPS
- Odoo credentials (admin/SmarterOS2026!)
- Revenue engine hook

---

## FASE 4: Web Scraping

### Qué es
Busca prospectos activos:
- Mercado Público licitaciones
- LinkedIn PYMEs Santiago
- Directorios empresariales
- LLM califica fit para SmarterOS

### Stack
- Python scrapy/requests
- LLM qualification
- Add to leads.json → auto-score → Kaggle export

### Deploy
- Script Python en VPS
- Cron cada 6 horas
- Filtros por industria/tamaño

---

## DEPENDENCIAS ENTRE FASES

```
Control Tower UI (1)
  ↓ necesita
Email Scraping (2) → muestra leads en tiempo real
  ↓ necesita
Auto-Facturación (3) → necesita leads calificados
  ↓ necesita
Web Scraping (4) → necesita facturación para cerrar
```

## SCORE PROYECTADO

| Dimensión | Actual | Fase 1 | Fase 2 | Fase 3 | Fase 4 | Final |
|-----------|--------|--------|--------|--------|--------|-------|
| Visualización | 5/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| Lead Gen | 10/15 | 10/15 | 13/15 | 13/15 | 15/15 | 15/15 |
| Revenue | 11/15 | 11/15 | 11/15 | 14/15 | 14/15 | 14/15 |
| Autonomía | 25/25 | 25/25 | 25/25 | 25/25 | 25/25 | 25/25 |
| TOTAL | 96/100 | 99/100 | 100/100 | 100/100 | 100/100 | 100/100 |

---

## EJECUCIÓN INMEDIATA

Voy a implementar TODO en orden, verificando cada paso antes de continuar.

### Checkpoint 1: Control Tower UI
- Crear HTML panel
- Deploy a VPS
- Caddy route
- Verify HTTPS

### Checkpoint 2: Email Scraping
- Crear workflow n8n
- Configurar IMAP
- Test end-to-end

### Checkpoint 3: Auto-Facturación
- Script Python
- Odoo API test
- Revenue hook

### Checkpoint 4: Web Scraping
- Scraper script
- Test con fuente real
- Cron setup

---
