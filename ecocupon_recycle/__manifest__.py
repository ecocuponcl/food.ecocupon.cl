{
    "name": "EcoCupon Recycle & Cashback",
    "version": "19.0.1.0.0",
    "category": "Sales/Point of Sale",
    "summary": "QR recycling + cashback rewards with anti-fraud validation",
    "description": """
EcoCupon Recycle & Cashback
============================
Turn waste into money:
- QR codes on products/packaging
- Scan to validate recycling
- Automatic cashback rewards
- Anti-fraud: GPS, photo, time windows, device fingerprint
- Integration with Flow.cl payments
    """,
    "author": "SmarterOS",
    "website": "https://food.ecocupon.cl",
    "license": "LGPL-3",
    "depends": ["sale", "website_sale", "food_kiosk"],
    "data": [
        "security/ir.model.access.csv",
        "data/recycle_sequence.xml",
        "data/recycle_categories.xml",
        "views/recycle_views.xml",
        "views/recycle_templates.xml",
        "views/recycle_menus.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "ecocupon_recycle/static/src/css/recycle.css",
            "ecocupon_recycle/static/src/js/recycle_scan.js",
        ],
    },
    "installable": True,
    "application": False,
}
