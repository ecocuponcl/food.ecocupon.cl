#!/bin/bash
# PicoClaw Config Sync — Mac → VPS
# Usage: ./picoclaw-sync.sh

VPS="root@89.116.23.167"
CONFIG="$HOME/.picoclaw/config.json"

if [ ! -f "$CONFIG" ]; then
    echo "❌ Config not found: $CONFIG"
    exit 1
fi

echo "📤 Syncing PicoClaw config to VPS..."
scp "$CONFIG" "$VPS:~/.picoclaw/config.json"

echo "🔄 Restarting PicoClaw gateway..."
ssh "$VPS" "docker restart picoclaw-gateway"

sleep 5

echo "✅ Status:"
ssh "$VPS" "docker ps --filter name=picoclaw --format '{{.Names}}: {{.Status}}'"
