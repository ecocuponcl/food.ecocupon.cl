from odoo import models, fields, api


class EcoWallet(models.Model):
    _name = "eco.wallet"
    _description = "EcoCupon Wallet"
    _rec_name = "phone"

    phone = fields.Char(string="Phone", required=True, index=True)
    partner_id = fields.Many2one("res.partner", string="Customer")
    balance = fields.Integer(string="Balance (CLP)", default=0)
    total_earned = fields.Integer(string="Total Earned (CLP)", compute="_compute_stats")
    total_recycled = fields.Integer(string="Items Recycled", compute="_compute_stats")
    transaction_ids = fields.One2many("eco.wallet.transaction", "wallet_id", string="Transactions")

    _sql_constraints = [
        ("phone_unique", "unique(phone)", "Phone number must be unique"),
    ]

    @api.depends("transaction_ids")
    def _compute_stats(self):
        for wallet in self:
            txs = wallet.transaction_ids
            wallet.total_earned = sum(txs.filtered(lambda t: t.type == "cashback").mapped("amount"))
            wallet.total_recycled = len(txs.filtered(lambda t: t.type == "cashback"))

    def action_withdraw(self, amount=None):
        """Withdraw balance for next purchase discount."""
        if amount is None:
            amount = self.balance
        if amount > self.balance:
            return {"type": "ir.actions.client", "tag": "display_notification",
                    "params": {"title": "Error", "message": "Saldo insuficiente", "type": "danger"}}

        self.env["eco.wallet.transaction"].create({
            "wallet_id": self.id,
            "type": "withdraw",
            "amount": -amount,
            "note": "Retiro para compra",
        })
        return {"type": "ir.actions.client", "tag": "display_notification",
                "params": {"title": "Éxito", "message": f"${amount} CLP retirados", "type": "success"}}


class EcoWalletTransaction(models.Model):
    _name = "eco.wallet.transaction"
    _description = "Wallet Transaction"
    _order = "create_date desc"

    wallet_id = fields.Many2one("eco.wallet", required=True, ondelete="cascade")
    type = fields.Selection([
        ("cashback", "Cashback Reciclaje"),
        ("withdraw", "Retiro"),
        ("adjustment", "Ajuste Manual"),
    ], required=True)
    amount = fields.Integer(required=True)
    recycle_event_id = fields.Many2one("eco.recycle.event", string="Recycle Event")
    qr_token_id = fields.Many2one("eco.qr.token", string="QR Token")
    note = fields.Text(string="Note")
