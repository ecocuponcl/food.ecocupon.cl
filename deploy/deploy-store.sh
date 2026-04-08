#!/bin/bash
# Deploy SmarterBOT Store to VPS
# Usage: ./deploy-store.sh

set -e

VPS="root@89.116.23.167"
REMOTE_DIR="/var/www/smarterbot-store"
LOCAL_DIR="$(cd "$(dirname "$0")/../landing-store" && pwd)"

echo "=== Deploying SmarterBOT Store to VPS ==="
echo "Local:  $LOCAL_DIR"
echo "Remote: $VPS:$REMOTE_DIR"

# Create remote directory if needed
ssh "$VPS" "mkdir -p $REMOTE_DIR"

# Upload files
echo "Uploading HTML files..."
scp "$LOCAL_DIR/index.html" "$VPS:$REMOTE_DIR/"
scp "$LOCAL_DIR/hosting.html" "$VPS:$REMOTE_DIR/"
scp "$LOCAL_DIR/clawbot.html" "$VPS:$REMOTE_DIR/"
scp "$LOCAL_DIR/kiosk.html" "$VPS:$REMOTE_DIR/"

echo "Uploading static files..."
scp "$LOCAL_DIR/sitemap.xml" "$VPS:$REMOTE_DIR/"
scp "$LOCAL_DIR/robots.txt" "$VPS:$REMOTE_DIR/"
scp "$LOCAL_DIR/favicon.svg" "$VPS:$REMOTE_DIR/"

echo "Uploading CSS/JS..."
ssh "$VPS" "mkdir -p $REMOTE_DIR/css $REMOTE_DIR/js"
scp "$LOCAL_DIR/css/style.css" "$VPS:$REMOTE_DIR/css/"
scp "$LOCAL_DIR/js/main.js" "$VPS:$REMOTE_DIR/js/"

# Reload Caddy if Caddyfile was updated
echo "Reloading Caddy..."
scp "$(dirname "$0")/../caddy/Caddyfile" "$VPS:/etc/caddy/Caddyfile"
ssh "$VPS" "caddy reload --config /etc/caddy/Caddyfile 2>&1 || systemctl reload caddy"

echo ""
echo "=== Deploy complete ==="
echo "Verify:"
echo "  curl -sI https://store.ecocupon.cl/"
echo "  curl -sI https://store.ecocupon.cl/hosting.html"
echo "  curl -sI https://store.ecocupon.cl/clawbot.html"
echo "  curl -sI https://store.ecocupon.cl/kiosk.html"
