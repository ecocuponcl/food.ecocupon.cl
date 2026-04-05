{
    "name": "EcoCupon Recycle & Cashback",
    "version": "17.0.1.0.0",
    "category": "Sales",
    "summary": "Reciclaje con cashback — convierte basura en dinero",
    "description": """
EcoCupon Recycle
================
- Genera QR único por envase post-compra
- Valida reciclaje (foto/GPS/camión)
- Acredita cashback en wallet del cliente
- Reportes de cumplimiento REP
    """,
    "depends": ["sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/eco_recycle_views.xml",
        "views/eco_recycle_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "eco_recycle/static/src/css/recycle.css",
            "eco_recycle/static/src/js/recycle.js",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
