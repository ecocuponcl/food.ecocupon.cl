# Domain & Cloudflare Monitor Skill

Monitors all domains/subdomains across Cloudflare accounts and Caddy config.
Detects SSL expiry, DNS issues, proxy misconfigurations, and orphaned domains.

## Triggers
- Cron: every 6 hours
- Manual: "revisa dominios", "check domains", "cloudflare status"
- Alert: SSL expiry < 7 days, DNS failure, Caddy config mismatch

## Tools Available
- `scripts/cf-domain-scan.sh` — Scan all Cloudflare zones
- `scripts/caddy-audit.sh` — Audit Caddyfile vs Cloudflare DNS
- `scripts/ssl-check.sh` — Check SSL certificate status

## Output Format
```json
{
  "scan_id": "uuid",
  "timestamp": "ISO8601",
  "domains": [
    {
      "domain": "example.com",
      "cloudflare_status": "active/proxied/dns_only",
      "ssl_status": "valid/expiring/expired",
      "ssl_days_left": 45,
      "caddy_configured": true,
      "caddy_status": "ok/mismatch/missing",
      "http_status": 200,
      "issues": ["SSL expiring in 5 days"]
    }
  ],
  "summary": {
    "total": 15,
    "healthy": 12,
    "warnings": 2,
    "critical": 1
  }
}
```

## Actions on Issues
1. **SSL expiring < 7 days** → Alert Telegram + auto-renew via Caddy
2. **DNS mismatch** → Alert + suggest fix
3. **Domain orphan** (in CF but not Caddy) → Report for cleanup
4. **Caddy domain not in CF** → Warning (possible misconfig)
