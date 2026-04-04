from odoo import models, fields


class RecycleCategory(models.Model):
    """Categorías de reciclaje: lata, botella, cartón, etc."""
    _name = 'recycle.category'
    _description = 'Recycle Category'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    icon = fields.Char(help='Emoji or icon identifier')
    default_cashback = fields.Float(string='Default Cashback (CLP)', default=100.0)
    description = fields.Text()
    active = fields.Boolean(default=True)

    # Anti-fraud
    require_photo = fields.Boolean(default=True)
    require_gps = fields.Boolean(default=False)
    max_scans_per_user_day = fields.Integer(default=5)
