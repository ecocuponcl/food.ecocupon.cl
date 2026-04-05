from odoo import models, fields, api


class EcoRecycleEvent(models.Model):
    _name = "eco.recycle.event"
    _description = "Recycle Event"
    _order = "create_date desc"

    qr_token_id = fields.Many2one("eco.qr.token", required=True, ondelete="restrict")
    wallet_id = fields.Many2one("eco.wallet", required=True)
    phone = fields.Char(related="wallet_id.phone", store=True)
    item = fields.Char(related="qr_token_id.item", store=True)
    reward = fields.Integer(related="qr_token_id.reward", store=True)
    validation_type = fields.Selection([
        ("photo", "Foto"),
        ("gps", "GPS"),
        ("truck", "Camión/Punto"),
    ], required=True)
    photo_url = fields.Char(string="Photo URL")
    lat = fields.Float(string="Latitude")
    lng = fields.Float(string="Longitude")
    order_id = fields.Many2one("sale.order", string="Original Order")
    state = fields.Selection([
        ("pending", "Pendiente"),
        ("validated", "Validado"),
        ("rejected", "Rechazado"),
    ], default="pending", required=True)

    def action_validate(self):
        """Validate recycle event and credit wallet. State guard prevents duplicates."""
        if self.state != "pending":
            return
        self.state = "validated"
        # Credit wallet
        self.env["eco.wallet.transaction"].create({
            "wallet_id": self.wallet_id.id,
            "type": "cashback",
            "amount": self.reward,
            "recycle_event_id": self.id,
            "qr_token_id": self.qr_token_id.id,
            "note": f"Cashback por reciclar {self.item}",
        })
        self.qr_token_id.used = True
        self.qr_token_id.recycled_at = fields.Datetime.now()
        self.qr_token_id.recycled_by_phone = self.phone
