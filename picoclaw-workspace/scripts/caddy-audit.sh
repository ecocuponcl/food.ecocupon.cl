#!/bin/bash
# Caddy Config Audit — PicoClaw Skill
# Compares Caddyfile domains with Cloudflare DNS + checks Caddy health
# Usage: ./caddy-audit.sh [CF_API_TOKEN]

set -euo pipefail

CADDYFILE="${CADDYFILE:-/etc/caddy/Caddyfile}"
CF_API_TOKEN="${1:-${CLOUDFLARE_API_TOKEN:-}}"
CF_API="https://api.cloudflare.com/client/v4"

echo "🔍 Auditing Caddy configuration..." >&2

# ── Extract domains from Caddyfile ────────────────────
CADDY_DOMAINS=$(grep -E '^\s*[a-zA-Z0-9._-]+\s*\{' "$CADDYFILE" | \
    sed 's/[[:space:]]*{.*//' | \
    sed '/^www\./d' | \  # Skip www redirects
    sort -u)

echo "📋 Caddy domains found:" >&2
echo "$CADDY_DOMAINS" | while read -r d; do echo "  → $d"; done >&2

# ── Build domain list with status ─────────────────────
echo "" >&2
echo "🔎 Checking each domain..." >&2

RESULTS="[]"

while IFS= read -r domain; do
    [ -z "$domain" ] && continue
    
    # HTTP check
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "https://$domain" 2>/dev/null || echo "000")
    
    # SSL check
    SSL_CHECK=$(echo | timeout 3 openssl s_client -connect "$domain:443" -servername "$domain" 2>/dev/null | \
        openssl x509 -noout -enddate -subject 2>/dev/null || echo "SSL_ERROR")
    
    # Extract expiry date
    SSL_EXPIRY=$(echo "$SSL_CHECK" | grep "notAfter=" | sed 's/notAfter=//' || echo "unknown")
    
    # Check if domain exists in Cloudflare
    CF_MATCH="unknown"
    if [ -n "$CF_API_TOKEN" ]; then
        BASE_DOMAIN=$(echo "$domain" | rev | cut -d. -f1-2 | rev)
        CF_CHECK=$(curl -s "$CF_API/zones?name=$BASE_DOMAIN" \
            -H "Authorization: Bearer $CF_API_TOKEN" | \
            python3 -c "import json,sys; d=json.load(sys.stdin); print('found' if d.get('result') else 'not_found')" 2>/dev/null || echo "error")
        CF_MATCH="$CF_CHECK"
    fi
    
    # Determine status
    STATUS="ok"
    ISSUES="[]"
    
    if [ "$HTTP_CODE" = "000" ]; then
        STATUS="critical"
        ISSUES='["Domain not responding"]'
    elif [ "$HTTP_CODE" -ge 500 ]; then
        STATUS="warning"
        ISSUES="[\"HTTP $HTTP_CODE - server error\"]"
    elif [ "$SSL_EXPIRY" = "unknown" ]; then
        STATUS="warning"
        ISSUES='["SSL certificate issue"]'
    fi
    
    if [ "$CF_MATCH" = "not_found" ]; then
        STATUS="warning"
        ISSUES="[\"Domain not in Cloudflare\"]"
    fi
    
    # Add to results
    RESULTS=$(echo "$RESULTS" | python3 -c "
import json, sys
results = json.load(sys.stdin)
results.append({
    'domain': '$domain',
    'http_status': int('$HTTP_CODE') if '$HTTP_CODE'.isdigit() else 0,
    'ssl_expiry': '''$SSL_EXPIRY'''.strip(),
    'cloudflare': '$CF_MATCH',
    'status': '$STATUS',
    'issues': json.loads('$ISSUES')
})
print(json.dumps(results))
")
done <<< "$CADDY_DOMAINS"

# ── Summary ───────────────────────────────────────────
echo "" >&2
echo "$RESULTS" | python3 -c "
import json, sys
domains = json.load(sys.stdin)
total = len(domains)
ok = sum(1 for d in domains if d['status'] == 'ok')
warn = sum(1 for d in domains if d['status'] == 'warning')
crit = sum(1 for d in domains if d['status'] == 'critical')

print(f'\n{\"=\"*60}')
print(f'📊 Caddy Audit Summary')
print(f'{\"=\"*60}')
print(f'  Total domains:  {total}')
print(f'  ✅ Healthy:     {ok}')
print(f'  ⚠️  Warnings:    {warn}')
print(f'  🚨 Critical:    {crit}')
print(f'{\"=\"*60}\n')

for d in domains:
    icon = {'ok': '✅', 'warning': '⚠️ ', 'critical': '🚨'}.get(d['status'], '❓')
    print(f\"  {icon} {d['domain']:40s} HTTP:{d['http_status']}  CF:{d['cloudflare']}\")
    for issue in d['issues']:
        print(f\"      └─ {issue}\")
print()
"

# ── JSON output for PicoClaw ─────────────────────────
echo "$RESULTS" | python3 -c "
import json, sys, uuid
domains = json.load(sys.stdin)
total = len(domains)
ok = sum(1 for d in domains if d['status'] == 'ok')
warn = sum(1 for d in domains if d['status'] == 'warning')
crit = sum(1 for d in domains if d['status'] == 'critical')

report = {
    'scan_id': str(uuid.uuid4()),
    'timestamp': __import__('datetime').datetime.utcnow().isoformat() + 'Z',
    'type': 'caddy_audit',
    'domains': domains,
    'summary': {
        'total': total,
        'healthy': ok,
        'warnings': warn,
        'critical': crit
    }
}
print(json.dumps(report, indent=2))
"
