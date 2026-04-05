#!/bin/bash
# PicoClaw Status — Check VPS gateway status
# Usage: ./picoclaw-status.sh

VPS="root@89.116.23.167"

echo "🤖 PicoClaw Gateway Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "📦 Container:"
ssh "$VPS" "docker ps --filter name=picoclaw --format '  Name: {{.Names}}\n  Status: {{.Status}}\n  Ports: {{.Ports}}'"

echo ""
echo "🔧 Config channels:"
ssh "$VPS" "python3 -c \"
import json
with open('/root/.picoclaw/config.json') as f:
    cfg = json.load(f)
for name, ch in cfg.get('channels', {}).items():
    status = '✅' if ch.get('enabled') else '❌'
    print(f'  {status} {name}')
\""

echo ""
echo "🌐 Ports:"
ssh "$VPS" "ss -tlnp | grep 1879"

echo ""
echo "💓 Health:"
ssh "$VPS" "curl -s http://localhost:18790/health 2>&1 | head -3 || echo '  ⚠️  Health endpoint not responding (normal for MaixCam mode)'"
