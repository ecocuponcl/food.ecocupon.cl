#!/usr/bin/env python3
"""
SmarterBOT Payment Telegram Bot
Telegram: 8530453742:AAGdKp9zTHN5hiQp4550gOzKwgmuGhOvgwQ
Commands: /start, /pagar, /productos, /confirmar, /help
"""
import os, json, httpx, re
from datetime import datetime

TG_TOKEN = "8530453742:AAGdKp9zTHN5hiQp4550gOzKwgmuGhOvgwQ"
N8N_URL = "https://n8n.smarterbot.store/webhook/payment-confirmed"
BOLT_API = "http://127.0.0.1:9011/api/bolt/bridge"
TG_API = f"https://api.telegram.org/bot{TG_TOKEN}"

PRICES = {
    "CLAWBOT": {"setup": 950000, "monthly": 190000, "uf_setup": 25, "uf_monthly": 5},
    "HOST": {"setup": 190000, "monthly": 76000, "uf_setup": 5, "uf_monthly": 2},
    "KIOSK": {"setup": 570000, "monthly": 114000, "uf_setup": 15, "uf_monthly": 3},
    "SUB": {"setup": 380000, "monthly": 380000, "uf_setup": 10, "uf_monthly": 10},
}

async def send_msg(chat_id, text, parse_mode="Markdown"):
    async with httpx.AsyncClient() as c:
        await c.post(f"{TG_API}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode})

async def handle_start(chat_id, user):
    await send_msg(chat_id, f"""Hola {user}! Soy el bot de pagos de SmarterBOT.

Comandos disponibles:
/productos - Ver catalogo y precios
/pagar <producto> [cantidad] - Cotizar
/confirmar - Confirmar pago pendiente
/help - Ayuda

Productos:
- CLAWBOT: 25 UF setup + 5 UF/mes
- Hosting: 5 UF setup + 2 UF/mes
- Kiosk: 15 UF setup + 3 UF/mes
- Subscription: 10 UF/mes""")

async def handle_productos(chat_id):
    msg = "Catalogo SmarterBOT\n\n"
    for code, p in PRICES.items():
        names = {"CLAWBOT": "CLAWBOT Kiosk", "HOST": "Hosting SmarterOS", "KIOSK": "Kiosk Setup", "SUB": "SmarterOS Subscription"}
        msg += f"*{names[code]}*\n  Setup: {p['uf_setup']} UF (${p['setup']:,} CLP)\n  Mensual: {p['uf_monthly']} UF (${p['monthly']:,} CLP)\n\n"
    msg += "Usa /pagar <producto> para cotizar"
    await send_msg(chat_id, msg)

async def handle_pagar(chat_id, msg_text):
    parts = msg_text.split()
    product = parts[1].upper() if len(parts) > 1 else "CLAWBOT"
    qty = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
    
    # Find matching product
    matched = None
    for code in PRICES:
        if code in product or product in code:
            matched = code
            break
    if not matched:
        await send_msg(chat_id, f"Producto no reconocido: {product}\nUsa /productos para ver el catalogo")
        return
    
    p = PRICES[matched]
    total_setup = p["setup"] * qty
    total_monthly = p["monthly"] * qty
    names = {"CLAWBOT": "CLAWBOT Kiosk", "HOST": "Hosting SmarterOS", "KIOSK": "Kiosk Setup", "SUB": "SmarterOS Subscription"}
    
    msg = f"Cotizacion SmarterBOT\n\n"
    msg += f"Producto: {names[matched]}\n"
    msg += f"Cantidad: {qty}\n"
    msg += f"Setup: ${total_setup:,} CLP ({p['uf_setup']*qty} UF)\n"
    msg += f"Mensual: ${total_monthly:,} CLP ({p['uf_monthly']*qty} UF/mes)\n\n"
    msg += f"Total inicial: ${total_setup:,} CLP\n\n"
    msg += f"Responde /confirmar para pagar ahora"
    await send_msg(chat_id, msg)
    
    # Send to n8n for processing
    try:
        async with httpx.AsyncClient() as c:
            await c.post("http://127.0.0.1:5678/webhook/payment-request", json={
                "chat_id": chat_id, "product": matched, "qty": qty,
                "total": total_setup, "monthly": total_monthly
            }, timeout=10)
    except:
        pass

async def handle_help(chat_id):
    await send_msg(chat_id, """Ayuda SmarterBOT

/pagar CLAWBOT 3 - Cotiza 3 kioskos CLAWBOT
/pagar HOST - Cotiza hosting
/confirmar - Paga cotizacion pendiente
/productos - Ver catalogo
/status - Ver estado del sistema

Precios en UF (1 UF = $38,000 CLP)
Pago via MercadoPago""")

async def handle_status(chat_id):
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get("http://127.0.0.1:9011/health", timeout=5)
            status = "OK" if r.status_code == 200 else "ERROR"
        await send_msg(chat_id, f"Estado del sistema: {status}\nBOLT API: {status}")
    except:
        await send_msg(chat_id, "Error consultando estado")

async def main():
    print(f"Payment bot starting... Token: {TG_TOKEN[:15]}...")
    offset = 0
    while True:
        try:
            async with httpx.AsyncClient() as c:
                r = await c.get(f"{TG_API}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35)
            if r.status_code == 200:
                updates = r.json().get("result", [])
                for u in updates:
                    offset = u["update_id"] + 1
                    msg = u.get("message", {})
                    chat_id = msg.get("chat", {}).get("id")
                    text = msg.get("text", "")
                    user = msg.get("from", {}).get("first_name", "User")
                    
                    if not chat_id or not text:
                        continue
                    
                    if text.startswith("/start"):
                        await handle_start(chat_id, user)
                    elif text.startswith("/pagar"):
                        await handle_pagar(chat_id, text)
                    elif text.startswith("/confirmar"):
                        await send_msg(chat_id, "Pago en proceso... Te enviamos el link de MercadoPago")
                    elif text.startswith("/productos"):
                        await handle_productos(chat_id)
                    elif text.startswith("/help"):
                        await handle_help(chat_id)
                    elif text.startswith("/status"):
                        await handle_status(chat_id)
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
