#!/bin/bash
# PicoClaw Logs — Stream VPS logs to local
# Usage: ./picoclaw-logs.sh [lines]

VPS="root@89.116.23.167"
LINES=${1:-50}

echo "📋 PicoClaw Gateway Logs (last $LINES lines):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ssh -t "$VPS" "docker logs -f picoclaw-gateway --tail $LINES"
