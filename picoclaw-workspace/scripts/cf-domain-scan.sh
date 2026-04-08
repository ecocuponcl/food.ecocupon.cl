#!/bin/bash
# Cloudflare Domain Scanner — PicoClaw Skill
# Scans ALL zones and domains in Cloudflare account
# Usage: ./cf-domain-scan.sh [CF_API_TOKEN]

set -euo pipefail

CF_API_TOKEN="${1:-${CLOUDFLARE_API_TOKEN:-}}"
CF_API="https://api.cloudflare.com/client/v4"
OUTPUT_FORMAT="${2:-json}"

if [ -z "$CF_API_TOKEN" ]; then
    echo '{"error": "CLOUDFLARE_API_TOKEN not set"}'
    exit 1
fi

# Headers
HEADERS="Authorization: Bearer $CF_API_TOKEN"
HEADERS="$HEADERS, Content-Type: application/json"

# ── Get all zones ─────────────────────────────────────
echo "🔍 Scanning Cloudflare zones..." >&2
ZONES=$(curl -s "$CF_API/zones" -H "Authorization: Bearer $CF_API_TOKEN" | \
    python3 -c "
import json, sys
data = json.load(sys.stdin)
if not data.get('success'):
    print(json.dumps({'error': data.get('errors', [])}))
    sys.exit(1)
for z in data['result']:
    print(json.dumps({
        'zone_id': z['id'],
        'zone_name': z['name'],
        'status': z['status'],
        'plan': z.get('plan', {}).get('name', 'unknown'),
        'paused': z['paused']
    }))
")

# ── Get all DNS records per zone ──────────────────────
ALL_DOMAINS="[]"

while IFS= read -r zone_json; do
    [ -z "$zone_json" ] && continue
    
    ZONE_ID=$(echo "$zone_json" | python3 -c "import json,sys; print(json.load(sys.stdin)['zone_id'])")
    ZONE_NAME=$(echo "$zone_json" | python3 -c "import json,sys; print(json.load(sys.stdin)['zone_name'])")
    ZONE_STATUS=$(echo "$zone_json" | python3 -c "import json,sys; print(json.load(sys.stdin)['status'])")
    
    echo "  📡 Zone: $ZONE_NAME ($ZONE_STATUS)" >&2
    
    DNS_RECORDS=$(curl -s "$CF_API/zones/$ZONE_ID/dns_records?per_page=100" \
        -H "Authorization: Bearer $CF_API_TOKEN" | \
        python3 -c "
import json, sys
data = json.load(sys.stdin)
results = []
for r in data.get('result', []):
    results.append({
        'domain': r['name'],
        'type': r['type'],
        'content': r['content'],
        'proxied': r.get('proxied', False),
        'ttl': r['ttl'],
        'zone': '$ZONE_NAME'
    })
print(json.dumps(results))
")
    
    ALL_DOMAINS=$(echo "$ALL_DOMAINS" | python3 -c "
import json, sys
base = json.load(sys.stdin)
new = json.loads('''$DNS_RECORDS''')
print(json.dumps(base + new))
")
done <<< "$ZONES"

# ── Check HTTP status + SSL for each domain ──────────
echo "🔒 Checking SSL and HTTP status..." >&2

FINAL=$(echo "$ALL_DOMAINS" | python3 -c "
import json, sys, subprocess

domains = json.load(sys.stdin)
results = []

for d in domains:
    if d['type'] not in ['A', 'AAAA', 'CNAME']:
        continue
    
    domain = d['domain']
    try:
        # Check SSL expiry
        result = subprocess.run(
            ['openssl', 's_client', '-connect', f'{domain}:443', '-servername', domain],
            input='Q', capture_output=True, text=True, timeout=5
        )
        ssl_info = subprocess.run(
            ['openssl', 'x509', '-noout', '-enddate'],
            input=result.stdout, capture_output=True, text=True, timeout=3
        )
        ssl_expiry = ssl_info.stdout.strip().replace('notAfter=', '')
    except:
        ssl_expiry = 'unknown'
    
    results.append({
        **d,
        'ssl_expiry': ssl_expiry
    })

print(json.dumps(results, indent=2))
")

# ── Output ────────────────────────────────────────────
if [ "$OUTPUT_FORMAT" = "json" ]; then
    echo "$FINAL"
else
    echo "$FINAL" | python3 -c "
import json, sys
domains = json.load(sys.stdin)
print(f'\n📊 Found {len(domains)} domains:\n')
for d in domains:
    proxy = '🟢 proxied' if d['proxied'] else '🟡 DNS only'
    print(f\"  {d['domain']:40s} {proxy:12s} TTL:{d['ttl']:6s}  SSL:{d['ssl_expiry']}\")
"
fi
