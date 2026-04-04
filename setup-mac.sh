#!/bin/bash
# ═══════════════════════════════════════════════════════════
# 🚀 Food Ecocupon — Mac Setup Script
# Installs agent + Cloudflare Tunnel
# Run on your Mac: bash setup-mac.sh
# ═══════════════════════════════════════════════════════════

set -e

echo "═══════════════════════════════════════════════════════"
echo "  🍔 Food Ecocupon — Mac Setup"
echo "═══════════════════════════════════════════════════════"
echo ""

# ── 1. Install dependencies ──────────────────────────────
echo "📦 Installing Python dependencies..."
pip3 install fastapi uvicorn requests python-dotenv 2>/dev/null && echo "✅ Done" || echo "⚠️  Check pip3 is installed"

# ── 2. Setup .env ────────────────────────────────────────
echo ""
echo "🔑 Setting up .env..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ .env created — EDIT WITH YOUR FLOW CREDENTIALS"
    echo "   Open .env and set FLOW_API_KEY and FLOW_SECRET_KEY"
else
    echo "⚠️  .env already exists — check credentials"
fi

# ── 3. Install cloudflared ──────────────────────────────
echo ""
echo "🌐 Installing Cloudflare Tunnel..."
if command -v cloudflared &> /dev/null; then
    echo "✅ cloudflared already installed: $(cloudflared --version)"
else
    echo "📥 Installing via brew..."
    brew install cloudflared 2>/dev/null || echo "⚠️  Install manually: brew install cloudflared"
fi

# ── 4. Login to Cloudflare ──────────────────────────────
echo ""
echo "🔐 Cloudflare login..."
echo "   This will open your browser to authenticate with Cloudflare"
cloudflared tunnel login 2>&1 || echo "⚠️  Login required"

# ── 5. Create tunnel ────────────────────────────────────
echo ""
echo "🚇 Creating tunnel..."
TUNNEL_NAME="ecocupon-agent"
if cloudflared tunnel list 2>/dev/null | grep -q "$TUNNEL_NAME"; then
    echo "✅ Tunnel '$TUNNEL_NAME' already exists"
else
    cloudflared tunnel create "$TUNNEL_NAME"
    echo "✅ Tunnel '$TUNNEL_NAME' created"
fi

# ── 6. Get Tunnel ID ────────────────────────────────────
TUNNEL_ID=$(cloudflared tunnel list 2>/dev/null | grep "$TUNNEL_NAME" | awk '{print $2}' | head -1)
echo ""
echo "🆔 Tunnel ID: $TUNNEL_ID"
echo ""
echo "⚠️  IMPORTANT: Update the DNS record in Cloudflare:"
echo "   agent.food.ecocupon.cl  →  CNAME  →  ${TUNNEL_ID}.cfargotunnel.com"
echo ""

# ── 7. Create config ────────────────────────────────────
CRED_FILE="$HOME/.cloudflared/${TUNNEL_ID}.json"
cat > config.yml << EOF
tunnel: $TUNNEL_ID
credentials-file: $CRED_FILE

ingress:
  - hostname: agent.food.ecocupon.cl
    service: http://localhost:9000
  - service: http_status:404
EOF
echo "✅ config.yml created"

# ── 8. Start services ───────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Starting services..."
echo "═══════════════════════════════════════════════════════"
echo ""
echo "Terminal 1 — Agent:"
echo "  uvicorn agent:app --host 0.0.0.0 --port 9000"
echo ""
echo "Terminal 2 — Tunnel:"
echo "  cloudflared tunnel run $TUNNEL_NAME"
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ✅ Setup complete!"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "🧪 Test:"
echo "  1. Visit https://agent.food.ecocupon.cl/health"
echo "  2. Should return: {\"status\":\"ok\"}"
echo ""
