#!/bin/bash
# Deploy all SmarterBOT multi-agent system to VPS
set -e

echo "🤖 Deploying SmarterBOT Multi-Agent System..."

# Copy agent files
scp deploy/agent-odoo.py root@89.116.23.167:/opt/smarterbot/
scp deploy/agent-n8n.py root@89.116.23.167:/opt/smarterbot/
scp deploy/agent-fastapi.py root@89.116.23.167:/opt/smarterbot/
scp deploy/agent-supabase.py root@89.116.23.167:/opt/smarterbot/
scp deploy/volt-reporter.py root@89.116.23.167:/opt/smarterbot/

echo "✅ Agent files deployed"

# Create systemd services on VPS
ssh root@89.116.23.167 '
# Create agent services
for agent in odoo n8n fastapi supabase; do
    cat > /etc/systemd/system/agent-${agent}.service << EOF
[Unit]
Description=SmarterBOT ${agent} Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/smarterbot
ExecStart=/usr/bin/python3 /opt/smarterbot/agent-${agent}.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=/opt/smarterbot/agent/.env

[Install]
WantedBy=multi-user.target
EOF
done

systemctl daemon-reload
for agent in odoo n8n fastapi supabase; do
    systemctl enable agent-${agent}
    systemctl start agent-${agent}
    sleep 2
    status=$(systemctl is-active agent-${agent})
    echo "  agent-${agent}: ${status}"
done

# Add volt-reporter cron (daily at 18:00)
echo "0 18 * * * cd /opt/smarterbot && python3 volt-reporter.py 2>/dev/null" >> /var/spool/cron/crontabs/root

echo "✅ All agents deployed"
echo "=== Agent Status ==="
for agent in odoo n8n fastapi supabase; do
    systemctl is-active agent-${agent}
done
echo "=== Cron ==="
crontab -l | grep -E "kaggle|scraper|volt"
'

echo "✅ Multi-agent system deployment complete"
