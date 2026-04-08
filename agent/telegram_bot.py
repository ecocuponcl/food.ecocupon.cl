"""
EcoCupon Telegram Admin Bot
============================
Commands:
  /start      - Welcome message
  /status     - Health check of all services
  /metrics    - Daily KPIs (recycles, cashback, active users)
  /conversion - Funnel metrics
  /decisions  - Last 10 agent decisions
  /health     - Detailed container health
  /help       - Command list
"""

import os
import logging
from datetime import datetime, timezone

import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ── Config ──────────────────────────────────────────────
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8690191913:AAEHOJMxdUj2UBSwrPlpW0jZfMUDwpUNWc")
AGENT_URL = os.getenv("AGENT_URL", "http://localhost:9000")
BOLT_URL = os.getenv("BOLT_URL", "http://localhost:8501")

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ── Helpers ─────────────────────────────────────────────
def safe_get(url: str, timeout: int = 5) -> dict | None:
    """Make a GET request, return parsed JSON or None."""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Request to {url} failed: {e}")
        return None


# ── Command Handlers ────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message about EcoCupon."""
    await update.message.reply_text(
        "\U0001f99e EcoCupon Bot v1.0\n\n"
        "\u267b\ufe0f Recicla, gana cashback, retira dinero.\n\n"
        "\U0001f4f1 \xBF C\u00f3mo funciona?\n"
        "1. Escanea el QR de tu envase en el kiosk\n"
        "2. Recibe cashback instant\u00e1neo\n"
        "3. Acumula y retira cuando quieras\n\n"
        "\U0001f4ca Comandos admin:\n"
        "/status \u2014 Estado del sistema\n"
        "/metrics \u2014 KPIs del d\u00eda\n"
        "/conversion \u2014 Funnel de conversi\u00f3n\n"
        "/decisions \u2014 Decisiones recientes\n"
        "/health \u2014 Estado de servicios\n"
        "/help \u2014 Esta ayuda",
        parse_mode="HTML",
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Health check of all services."""
    services_status = []

    # Check Agent API
    agent_health = safe_get(f"{AGENT_URL}/health")
    if agent_health:
        status_icon = "\u2705" if agent_health.get("status") == "ok" else "\u274c"
        services_status.append(f"{status_icon} Agent API ({agent_health.get('active_llm', 'unknown')})")
    else:
        services_status.append("\u274c Agent API (no responde)")

    # Check Bolt Dashboard
    bolt_health = safe_get(f"{BOLT_URL}/_stcore/health")
    if bolt_health:
        services_status.append("\u2705 Bolt Dashboard")
    else:
        services_status.append("\u274c Bolt Dashboard")

    # Check Odoo Kiosk
    odoo_health = safe_get("http://localhost:8070")
    if odoo_health:
        services_status.append("\u2705 Odoo Kiosk")
    else:
        services_status.append("\u274c Odoo Kiosk")

    # Check n8n
    n8n_health = safe_get("http://localhost:5678/healthz")
    if n8n_health:
        services_status.append("\u2705 n8n")
    else:
        services_status.append("\u274c n8n")

    # Check Caddy
    caddy_health = safe_get("http://localhost:2019/metrics")
    if caddy_health:
        services_status.append("\u2705 Caddy")
    else:
        services_status.append("\u274c Caddy")

    msg = "\U0001f493 Estado del Sistema\n" + \
          f"\U0001f553 {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}\n\n" + \
          "\n".join(services_status)

    await update.message.reply_text(msg)


async def metrics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Daily KPIs."""
    try:
        stats = safe_get(f"{AGENT_URL}/recycle/stats")
        if not stats:
            await update.message.reply_text("\u274c No se pudieron obtener m\u00e9tricas del agent")
            return

        total_recycles = stats.get("total_recycles", 0)
        total_cashback = stats.get("total_cashback_clp", 0)
        active_wallets = stats.get("active_wallets", 0)
        items_recycled = stats.get("items_recycled", {})

        items_text = ""
        for item, count in items_recycled.items():
            items_text += f"  \u2022 {item}: {count}\n"

        msg = (
            f"\U0001f4ca M\u00e9tricas del D\u00eda\n\n"
            f"\u267b\ufe0f Reciclajes totales: {total_recycles}\n"
            f"\U0001f4b0 Cashback acumulado: ${total_cashback:,} CLP\n"
            f"\U0001f465 Wallets activos: {active_wallets}\n\n"
            f"\U0001f4e6 Items reciclados:\n{items_text or '  (ninguno a\u00fan)'}"
        )
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"\u274c Error: {str(e)}")


async def conversion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Funnel metrics."""
    try:
        # Try to get conversion data from agent
        stats = safe_get(f"{AGENT_URL}/recycle/stats")
        total_recycles = stats.get("total_recycles", 0) if stats else 0

        # Build funnel from available data
        msg = (
            f"\U0001f4ca Funnel de Conversi\u00f3n\n\n"
            f"\U0001f441\ufe0f  Visitantes: (tracking pendiente)\n"
            f"\U0001f6d2 Carritos: (tracking pendiente)\n"
            f"\U0001f4b3 Pagos: (tracking pendiente)\n"
            f"\u267b\ufe0f  Reciclajes: {total_recycles}\n\n"
            f"\U0001f4c8 Tasa: (necesita m\u00e1s datos)"
        )
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"\u274c Error: {str(e)}")


async def decisions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Last 10 agent decisions."""
    try:
        # Get recent decisions from recycle events
        health = safe_get(f"{AGENT_URL}/health")
        if not health:
            await update.message.reply_text("\u274c No se pudo conectar al agent")
            return

        total_recycles = health.get("recycles", 0)

        if total_recycles == 0:
            msg = "\U0001f916 \u00daltimas decisiones del agente:\n\n(a\u00fan no hay decisiones registradas)"
        else:
            msg = (
                f"\U0001f916 \u00daltimas decisiones del agente:\n\n"
                f"\u2022 Total decisiones: {total_recycles}\n"
                f"\u2022 QR tokens activos: {health.get('qr_tokens', 0)}\n"
                f"\u2022 Wallets: {health.get('wallets', 0)}\n\n"
                f"Consulta /metrics para ver el detalle."
            )

        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"\u274c Error: {str(e)}")


async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detailed container health."""
    try:
        resp = safe_get(f"{AGENT_URL}/health")
        if not resp:
            await update.message.reply_text("\u274c Agent no responde")
            return

        status_icon = "\u2705 OK" if resp.get("status") == "ok" else "\u274c DOWN"
        active_llm = resp.get("active_llm", "N/A")
        latency = resp.get("latency_ms", "N/A")
        llm_failover = resp.get("llm_failover", {})

        msg = (
            f"\U0001f3e5 Health Detallado\n\n"
            f"API: {status_icon}\n"
            f"LLM Activo: {active_llm}\n"
            f"Latencia: {latency} ms\n"
            f"LLM Failover:\n"
            f"  \u2022 Local Ollama: {'\u2705' if llm_failover.get('local_ollama') else '\u274c'}\n"
            f"  \u2022 Cloudflare AI: {'\u2705' if llm_failover.get('cloudflare_ai') else '\u274c'}\n\n"
            f"Supabase: {'\u2705' if resp.get('supabase_configured') else '\u274c'}\n"
            f"n8n: {'\u2705' if resp.get('n8n_configured') else '\u274c'}\n"
            f"OpenRouter: {'\u2705' if resp.get('llm_configured') else '\u274c'}\n\n"
            f"Wallets: {resp.get('wallets', 0)}\n"
            f"Reciclajes: {resp.get('recycles', 0)}\n"
            f"QR Tokens: {resp.get('qr_tokens', 0)}"
        )
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"\u274c Error: {str(e)}")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List of commands."""
    await update.message.reply_text(
        "\U0001f4cb Comandos disponibles:\n\n"
        "/start \u2014 Iniciar bot\n"
        "/status \u2014 Estado del sistema\n"
        "/metrics \u2014 KPIs del d\u00eda\n"
        "/conversion \u2014 Funnel de conversi\u00f3n\n"
        "/decisions \u2014 Decisiones recientes\n"
        "/health \u2014 Estado de servicios\n"
        "/help \u2014 Esta ayuda",
        parse_mode="HTML",
    )


# ── Main ────────────────────────────────────────────────
def main():
    """Start the bot."""
    logger.info("Starting EcoCupon Telegram Bot...")

    app = Application.builder().token(BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("metrics", metrics))
    app.add_handler(CommandHandler("conversion", conversion))
    app.add_handler(CommandHandler("decisions", decisions))
    app.add_handler(CommandHandler("health", health))
    app.add_handler(CommandHandler("help", help_cmd))

    logger.info("Bot handlers registered. Starting polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
