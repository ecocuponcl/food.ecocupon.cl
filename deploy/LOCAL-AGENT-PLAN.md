# 🧠 SMARTEROS v5 — LOCAL AGENT + KAGGLE BENCHMARKS

## HARDWARE ACTUAL (VPS)

| Recurso | Valor | Limitación |
|---------|-------|------------|
| CPU | 2 cores | Limitado para LLM local |
| RAM | 7.9GB (2.2GB libre) | Tight para vector DB |
| Disco | 39GB libre | Suficiente |
| Red | Cloudflare proxy | Latencia OK |

## ESTRATEGIA REALISTA

### NO hacer en VPS:
- ❌ LLM local cuantizado (requiere 4+ cores, 8+ GB RAM)
- ❌ ChromaDB/Qdrant completo (overhead alto)
- ❌ Inferencia asíncrona masiva (2 cores limitan)

### SÍ hacer en VPS:
- ✅ Kaggle benchmarks sync (API calls, ligero)
- ✅ Scoring model tuning (estadístico, no ML pesado)
- ✅ Auto-tuning de reglas (lógica simple)
- ✅ Memoria de largo plazo (SQLite + embeddings simples)
- ✅ Bridge API para agente externo (Mac Mini/Orange Pi)

## ARQUITECTURA v5

```
┌─────────────────────────────────────────────┐
│              VPS (2 cores, 8GB)             │
│                                             │
│  ┌─────────────────┐  ┌──────────────────┐  │
│  │ Kaggle Bridge   │  │ Scoring Tuner    │  │
│  │ - Sync benchmarks│  │ - Auto-adjust    │  │
│  │ - Compare models│  │ - Rule tuning    │  │
│  │ - Update weights│  │ - A/B testing    │  │
│  └────────┬────────┘  └────────┬─────────┘  │
│           │                    │            │
│  ┌────────┴────────────────────┴─────────┐  │
│  │        Local Memory (SQLite)          │  │
│  │  - Lead history                       │  │
│  │  - Conversation cache                 │  │
│  │  - Pattern recognition                │  │
│  └───────────────────┬───────────────────┘  │
│                      │                      │
│  ┌───────────────────┴───────────────────┐  │
│  │       External Agent Bridge           │  │
│  │  - POST /api/agent/analyze            │  │
│  │  - POST /api/agent/sync               │  │
│  │  - GET  /api/agent/status             │  │
│  └───────────────────┬───────────────────┘  │
└──────────────────────┼──────────────────────┘
                       │
              ┌────────┴─────────┐
              │  Mac Mini /      │
              │  Orange Pi       │
              │  (Volt AGI)      │
              │                  │
              │  - Heavy LLM     │
              │  - Vector DB     │
              │  - Async queue   │
              └──────────────────┘
```

## FASES DE IMPLEMENTACIÓN

### Fase 1: Kaggle Benchmarks Bridge
- Descargar metadata de competencias relevantes
- Comparar scoring actual vs benchmarks
- Auto-adjust weights basado en performance

### Fase 2: Local Memory System
- SQLite para persistencia ligera
- Simple embeddings para similarity search
- Lead conversation history

### Fase 3: Auto-Tuning Engine
- Analizar éxito/fracaso de reglas
- Proponer ajustes automáticos
- A/B testing de scoring models

### Fase 4: External Agent Bridge
- API endpoints para agente externo
- Sync bidireccional
- Health monitoring

## SCORE PROYECTADO

| Dimensión | Actual | v5 | Δ |
|-----------|--------|----|---|
| Infra | 30/30 | 30/30 | = |
| Autonomía | 25/25 | 25/25 | = |
| Lead Gen | 14/15 | 15/15 | +1 |
| Revenue | 13/15 | 14/15 | +1 |
| ML/AI | 5/10 | 9/10 | +4 |
| **TOTAL** | **92/100** | **97/100** | **+5** |
