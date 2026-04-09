# 🤖 SMARTEROS v7 — AGENT DELEGATION PLAN

## AUDIT RESULT (2 passes)

### Current State
| Tool | Status | Issues |
|------|--------|--------|
| **Odoo** | ✅ Connected (UID:2) | 0 CRM leads, 7 partners, 1 POS |
| **n8n** | ✅ 2 workflows | MCP down, need 8 WF synced |
| **n8n MCP** | ❌ Port 8101 not responding | Container exists but not reachable |
| **FastAPI** | ✅ 8 services | lead-webhook, agent, bolt, revenue, etc. |
| **Supabase** | ✅ Online | URL: rjfcmmzjlguiititkmyh.supabase.co |
| **Kaggle** | ✅ Dataset + Notebook | Auto-export every 5 min |
| **Telegram** | ✅ Bot active | 7631713367 → Chat: 6683244662 |
| **Caddy** | ✅ 200 on all HTTPS | Fixed duplicate blocks |
| **Docker** | ✅ 21 containers | n8n, Odoo, DBs, Redis, etc. |
| **Services** | ✅ 10/10 active | 1 activating (agent-bridge) |

---

## AGENT DELEGATION (1 per tool)

```
┌─────────────────────────────────────────────────────────┐
│                    VOLT REPORTER                         │
│              (Daily Summary → Telegram)                  │
│                         :9011                            │
└──────┬─────────┬──────────┬──────────┬──────────────────┘
       │         │          │          │
  ┌────┴──┐ ┌────┴───┐ ┌───┴────┐ ┌───┴─────┐
  │ Odoo   │ │  n8n   │ │ FastAPI│ │ Supab.  │
  │ Agent  │ │ Agent  │ │ Agent  │ │ Agent   │
  │ :9020  │ │ :9021  │ │ :9022  │ │ :9023   │
  └────────┘ └────────┘ └────────┘ └─────────┘
       │         │          │          │
  ┌────┴──┐ ┌────┴───┐ ┌───┴────┐ ┌───┴─────┐
  │Kaggle │ │Telegram│ │  Caddy │ │ Docker  │
  │ Agent │ │ Agent  │ │ Agent  │ │ Agent   │
  │ :9024 │ │ :9025  │ │ :9026  │ │ :9027   │
  └────────┘ └────────┘ └────────┘ └─────────┘
```

---

## 8 SPECIALIZED AGENTS

### 1. 🏢 Odoo Agent (✅ existing)
- **Port:** 9020
- **Monitors:** DB, CRM, POS, Partners, Invoices
- **Auto-repairs:** Restart Odoo, create missing leads, fix POS
- **Reports:** CRM status, lead sync, invoice count
- **Cron:** Every 30 min

### 2. ⚡ n8n Agent (✅ existing)
- **Port:** 9021
- **Monitors:** n8n service, workflows, executions, DB size
- **Auto-repairs:** Restart n8n, clean old executions, fix webhooks
- **Reports:** Workflow status, error rate, execution count
- **Cron:** Every 30 min

### 3. 🌐 FastAPI Agent (✅ existing)
- **Port:** 9022
- **Monitors:** 8 FastAPI services (webhook, agent, bolt, revenue, qr, alerts, invoice, bridge)
- **Auto-repairs:** Restart failed services, clear cache
- **Reports:** Service health, latency, uptime
- **Cron:** Every 30 min

### 4. 🗃️ Supabase Agent (✅ existing)
- **Port:** 9023
- **Monitors:** API, 7 critical tables, RLS, storage
- **Auto-repairs:** Retry failed queries, backup to JSON
- **Reports:** Table row counts, API latency, RLS status
- **Cron:** Every 1 hour

### 5. 🏆 Kaggle Agent (NEW)
- **Port:** 9024
- **Monitors:** Dataset sync, notebook status, benchmark scores
- **Auto-repairs:** Re-sync CSVs, re-push notebook
- **Reports:** Dataset freshness, model scores, leaderboard position
- **Cron:** Every 12 hours (aligned with existing cron)

### 6. 📱 Telegram Agent (NEW)
- **Port:** 9025
- **Monitors:** Bot uptime, message delivery, chat activity
- **Auto-repairs:** Restart bot, resend failed messages
- **Reports:** Message count, error rate, response time
- **Cron:** Every 1 hour

### 7. 🔒 Caddy Agent (NEW)
- **Port:** 9026
- **Monitors:** All HTTPS endpoints, SSL cert expiry, DNS
- **Auto-repairs:** Restart Caddy, fix duplicate blocks, request certs
- **Reports:** Endpoint status, cert days-to-expiry, DNS health
- **Cron:** Every 1 hour

### 8. 🐳 Docker Agent (NEW)
- **Port:** 9027
- **Monitors:** 21 containers, disk usage, RAM, network
- **Auto-repairs:** Restart crashed containers, prune images, clean logs
- **Reports:** Container status, disk %, RAM usage, restart count
- **Cron:** Every 30 min

---

## SYNCHRONIZATION MATRIX

| Agent | Reports To | Syncs With | Trigger |
|-------|-----------|------------|---------|
| Odoo | Volt + Telegram | n8n, FastAPI | 30 min |
| n8n | Volt + Telegram | Odoo, Kaggle | 30 min |
| FastAPI | Volt + Telegram | All agents | 30 min |
| Supabase | Volt + Telegram | Kaggle | 1 hour |
| Kaggle | Volt + Telegram | Supabase, n8n | 12 hours |
| Telegram | Volt | All agents | 1 hour |
| Caddy | Volt + Telegram | FastAPI, Docker | 1 hour |
| Docker | Volt | Caddy, All | 30 min |
| **Volt Reporter** | **Telegram** | **All 8 agents** | **18:00 daily** |

---

## IMPLEMENTATION ORDER

```
Step 1: Fix n8n MCP (port 8101 down)
Step 2: Create 4 new agents (Kaggle, Telegram, Caddy, Docker)
Step 3: Create systemd services for all 8 agents
Step 4: Test each agent individually
Step 5: Update Volt Reporter to collect from all 8
Step 6: Deploy daily report at 18:00
Step 7: Final verification
```

---

## EXPECTED OUTCOME

| Metric | Before | After |
|--------|--------|-------|
| Agents | 4 | 8 |
| Monitoring coverage | 60% | 100% |
| Auto-repair tools | 4 | 8 |
| Report frequency | Manual | Every 30 min + daily summary |
| Docker visibility | None | Full container monitoring |
| SSL monitoring | None | Cert expiry alerts |
| Telegram monitoring | None | Bot health + delivery tracking |
| Kaggle sync | Manual cron | Agent-managed with alerts |
