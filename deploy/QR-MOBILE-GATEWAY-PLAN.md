# 🔗 QR.SMARTERBOT.STORE — Mobile Gateway Integration Plan

## ESTADO ACTUAL

| Componente | Estado | Detalle |
|------------|--------|---------|
| `qr.ecocupon.cl` | ✅ 89.116.23.167 | QR Validator funcionando |
| `qr.ecocupon.smarterbot.store` | ✅ Caddy configurado | Proxy a :9004 |
| `qr.smarterbot.store` | ❌ 188.114.97.3 | Cloudflare placeholder (NO VPS) |
| QR Validator API | ✅ :9004 | Health OK, bolt_api :9010 |
| Revenue Engine | ✅ Running | 13 leads scored |
| BOLT v3 Balance | ✅ Running | balanced(100.0) |

## PROBLEMA

`qr.smarterbot.store` resuelve a Cloudflare (188.114.97.3), NO a nuestro VPS.
Necesitamos crear este subdominio como **Mobile Gateway** para conectar:
- Móvil del cliente → QR scan → Revenue Engine → Google CRM → Trello

## ORDEN LÓGICO DE IMPLEMENTACIÓN

```
1. DNS: Crear qr.smarterbot.store → 89.116.23.167 (Cloudflare)
2. Caddy: Agregar ruta qr.smarterbot.store → QR Validator
3. Mobile Gateway: QR dinámico → lead tracking
4. Revenue Integration: QR scan → scoring → action
5. Kaggle MCP: Model integration for scoring
6. Test completo: QR scan → revenue action
```

## IMPLEMENTACIÓN

### Paso 1: DNS + Caddy
- Crear A record: qr.smarterbot.store → 89.116.23.167
- Caddy route: qr.smarterbot.store → /var/www/qr-validator + proxy :9004

### Paso 2: Mobile Gateway (QR Dinámico)
```python
# /var/www/qr-validator/mobile-gateway.py
# Endpoint: qr.smarterbot.store/scan/{lead_id}
# - Generates unique QR for each lead
# - Tracks scan events
# - Triggers revenue engine action
# - Updates Trello card
# - Syncs with Google Calendar
```

### Paso 3: Revenue Integration
- QR scan → update lead score
- If score > 70 → trigger close sequence
- Update Trello card status
- Create Google Calendar event

### Paso 4: Kaggle MCP Integration
- Connect model predictions to lead scoring
- Use MCP server for real-time model updates
- Export leads to Kaggle dataset for analysis

## SCORE PROYECTADO

| Dimensión | Antes | Después |
|-----------|-------|---------|
| Mobile Integration | 0/10 | 10/10 |
| QR Revenue | 0/15 | 15/15 |
| TOTAL | 100/100 | 100/100 (con mobile) |
