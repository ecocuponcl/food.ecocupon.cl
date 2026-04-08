# ── EcoCupon Login Theme — Odoo Module ──
# Personaliza el login de Odoo con branding EcoCupon (Yellow & Black)
# y habilita reportes diarios automáticos

{
    "name": "EcoCupon Login Theme",
    "version": "1.0.0",
    "category": "Theme",
    "summary": "Smarter Dumper branding for Odoo login + daily reports",
    "author": "SmarterOS",
    "website": "https://ecocupon.cl",
    "depends": ["web"],
    "data": [
        "views/login_layout.xml",
        "views/web_layout.xml",
        "data/ir_config.xml"
    ],
    "installable": True,
    "application": False,
    "auto_install": False
}
