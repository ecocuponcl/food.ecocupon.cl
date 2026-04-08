#!/usr/bin/env python3
"""Add cyberpunk branding to Telegram bot"""

with open("/opt/smarter-telegram-bot/bot.py", "r") as f:
    content = f.read()

# Add cyberpunk welcome message before cmd_start
old_start = 'async def cmd_start'
new_start = '''CYBERPUNK_WELCOME = "\\U0001f99e *SMARTEROS ACTIVATED* \\U0001f99e\\n\\n\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\n\\u2588\\u2580\\u2580 \\u2588\\u2580\\u2588 \\u2588\\u2580\\u2580 \\u2588\\u00b0\\u2588 \\u2588\\u2580\\u2580\\n\\u2588\\u2584\\u2584 \\u2588\\u2580\\u2584 \\u2588\\u2588\\u2584 \\u2588\\u2580\\u2588 \\u2588\\u2588\\u2584\\n\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\n\\n_Bienvenido al ecosistema EcoCupon_\\n_Recicl\\u00e1. Gan\\u00e1. Repet\\u00ed._\\n\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501"

async def cmd_start'''

content = content.replace(old_start, new_start)

# Use the welcome message in cmd_start
content = content.replace(
    'await message.reply_text("Bienvenido',
    'await message.reply_text(CYBERPUNK_WELCOME, parse_mode="Markdown")\\n\\n    await message.reply_text("Bienvenido'
)

with open("/opt/smarter-telegram-bot/bot.py", "w") as f:
    f.write(content)

print("Cyberpunk branding added to Telegram bot")
