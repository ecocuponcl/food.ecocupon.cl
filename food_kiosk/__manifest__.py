{
    "name": "Food Kiosk",
    "version": "19.0.1.0.0",
    "category": "Sales/Point of Sale",
    "summary": "Kiosk touch-screen ordering + Flow.cl payment integration",
    "description": """
Food Kiosk
==========
Kiosk mode for touch-screen ordering with:
- Full-screen kiosk UI (vertical 480px layout)
- Product browsing via tabs
- One-tap order creation
- Flow.cl payment redirect
- Webhook-based order confirmation
    """,
    "author": "SmarterOS",
    "website": "https://food.ecocupon.cl",
    "license": "LGPL-3",
    "depends": ["sale", "website_sale"],
    "data": [
        "data/kiosk_data.xml",
        "security/ir.model.access.csv",
        "views/food_kiosk_templates.xml",
        "views/food_kiosk_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "food_kiosk/static/src/css/kiosk.css",
            "food_kiosk/static/src/js/kiosk.js",
        ],
    },
    "installable": True,
    "application": False,
}
