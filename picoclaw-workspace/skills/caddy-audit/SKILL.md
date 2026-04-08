# Caddy Configuration Audit Skill

Audits Caddy reverse proxy configuration against Cloudflare DNS records.
Detects mismatches, orphaned domains, SSL issues, and misconfigurations.

## Triggers
- Cron: every 4 hours
- Manual: "revisa caddy", "audit caddy", "check caddyfile"
- Alert: Domain down, SSL expired, config mismatch

## What It Checks

### 1. Domain Inventory
- Extracts ALL domains from `/etc/caddy/Caddyfile`
- Compares with Cloudflare DNS zones
- Identifies orphaned domains (in CF but not Caddy, or vice versa)

### 2. SSL Certificate Health
- Checks Let's Encrypt expiry for each domain
- Alerts when SSL expires in < 7 days
- Verifies auto-renewal is working

### 3. HTTP Health
- GET request to each domain (HTTPS)
- Detects 5xx errors, timeouts, connection refused
- Verifies reverse proxy backend is responding

### 4. Caddy Service Health
- `systemctl status caddy` — running?
- `caddy validate` — config valid?
- Caddy process memory/CPU usage

## Scripts
- `scripts/caddy-audit.sh` — Full audit report
- `scripts/cf-domain-scan.sh` — Cloudflare zone scan

## Auto-Remediation
When issues are detected:
1. **SSL expiring soon** → `caddy reload` to force renewal
2. **Caddy config invalid** → `caddy validate` then alert
3. **Backend down** → Alert Telegram immediately
4. **Orphan domain** → Report for cleanup decision

## Output to n8n
Sends audit results to n8n webhook for:
- PostgreSQL logging (`smarter_events` table)
- Telegram notification if warnings/critical
- Dashboard update (Bolt Streamlit)
