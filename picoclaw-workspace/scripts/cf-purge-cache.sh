#!/bin/bash
# cf-purge-cache.sh — Purge Cloudflare cache for ecocupon.cl
# Usage: bash cf-purge-cache.sh [API_TOKEN]
# Token must have: Zone:Cache Purge:Edit

set -e

CF_TOKEN="${1:-}"
ZONE="ecocupon.cl"

# Find token from env or default
if [ -z "$CF_TOKEN" ]; then
    CF_TOKEN="${CLOUDFLARE_API_TOKEN:-}"
fi

if [ -z "$CF_TOKEN" ]; then
    echo "❌ No Cloudflare API token provided"
    echo "Usage: $0 <token>"
    echo "   or: export CLOUDFLARE_API_TOKEN=xxx && $0"
    exit 1
fi

# Get zone ID
ZONE_ID=$(curl -s "https://api.cloudflare.com/client/v4/zones?name=$ZONE" \
    -H "Authorization: Bearer $CF_TOKEN" | \
    python3 -c "import sys,json; print(json.load(sys.stdin)['result'][0]['id'])" 2>/dev/null)

if [ -z "$ZONE_ID" ]; then
    echo "❌ Could not find zone: $ZONE"
    exit 1
fi

echo "🧹 Purging cache for zone: $ZONE ($ZONE_ID)"

# Purge everything
RESULT=$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" \
    -H "Authorization: Bearer $CF_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"purge_everything":true}')

SUCCESS=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['success'])")

if [ "$SUCCESS" = "True" ]; then
    echo "✅ Cache purged successfully"
    echo "⏳ Wait 30-60s for fresh fetch from origin"
else
    echo "❌ Failed: $RESULT"
    exit 1
fi
