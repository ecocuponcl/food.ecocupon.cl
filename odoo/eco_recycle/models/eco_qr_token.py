import uuid
from odoo import models, fields, api


class EcoQRToken(models.Model):
    _name = "eco.qr.token"
    _description = "QR Token for Packaging"

    token = fields.Char(required=True, index=True, readonly=True)
    order_id = fields.Many2one("sale.order", required=True, ondelete="restrict")
    item = fields.Char(string="Item Type", required=True,
                       help="Tipo de envase: sixpack, botella, lata, etc.")
    reward = fields.Integer(string="Reward (CLP)", required=True)
    used = fields.Boolean(default=False)
    created_at = fields.Datetime(default=fields.Datetime.now)
    recycled_at = fields.Datetime()
    recycled_by_phone = fields.Char()
    recycle_event_id = fields.Many2one("eco.recycle.event", string="Recycle Event")

    _sql_constraints = [
        ("token_unique", "unique(token)", "Token must be unique"),
    ]

    @api.model
    def create_from_order(self, order_id, item, reward):
        """Create QR token after a purchase."""
        token = uuid.uuid4().hex[:16]
        return self.create({
            "token": token,
            "order_id": order_id,
            "item": item,
            "reward": reward,
        })

    def get_qr_url(self):
        self.ensure_one()
        return f"https://food.ecocupon.cl/recycle/scan?t={self.token}"
