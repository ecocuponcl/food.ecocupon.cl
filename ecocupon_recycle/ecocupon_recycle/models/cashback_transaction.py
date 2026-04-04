from odoo import models, fields, api


class CashbackTransaction(models.Model):
    """Registro de cada cashback pagado"""
    _name = 'cashback.transaction'
    _description = 'Cashback Transaction'
    _order = 'create_date desc'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    item_id = fields.Many2one('recycle.item', string='Item')
    event_id = fields.Many2one('recycle.event', string='Event')
    order_id = fields.Many2one('sale.order', string='Original Order')

    amount = fields.Float(required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.CLP', raise_if_not_found=False))

    status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
        ('fraud_reversed', 'Fraud Reversed'),
    ], default='pending', required=True, index=True)

    source = fields.Selection([
        ('recycle', 'Recycling'),
        ('purchase', 'Purchase Bonus'),
        ('referral', 'Referral'),
        ('promo', 'Promotion'),
        ('manual', 'Manual Adjustment'),
    ], default='recycle')

    # Payment tracking
    payment_method = fields.Selection([
        ('flow', 'Flow.cl'),
        ('credit', 'Store Credit'),
        ('transfer', 'Bank Transfer'),
    ], default='credit')

    paid_at = fields.Datetime()
    payment_ref = fields.Char()

    # Anti-fraud
    fraud_flag = fields.Boolean(default=False)
    fraud_reason = fields.Char()

    # Sync
    synced_to_supabase = fields.Boolean(default=False)
    tenant_id = fields.Char(default='ecocupon', index=True)

    def action_mark_paid(self):
        self.write({
            'status': 'paid',
            'paid_at': fields.Datetime.now(),
        })

    def action_flag_fraud(self, reason=''):
        self.write({
            'status': 'fraud_reversed',
            'fraud_flag': True,
            'fraud_reason': reason,
        })
        # Reverse credits
        for tx in self:
            if tx.partner_id:
                tx.partner_id.recycle_credits -= tx.amount
