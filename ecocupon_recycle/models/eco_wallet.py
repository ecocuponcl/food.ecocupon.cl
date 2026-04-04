"""
AJUSTE 2: Wallet interna separada de Flow.cl
Flow solo para pagos y retiros — wallet maneja cashback
"""
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    eco_wallet_id = fields.One2many('eco.wallet', 'partner_id', string='Eco Wallet')
    recycle_count = fields.Integer(string='Items Recycled', default=0)
    recycle_qr_code = fields.Char(string='Personal QR Code', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        for partner in partners:
            if not partner.recycle_qr_code:
                partner.recycle_qr_code = f"USER-{partner.id:06d}"
            # Crear wallet automática
            self.env['eco.wallet'].create({
                'partner_id': partner.id,
                'currency_id': self.env.ref('base.CLP', raise_if_not_found=False).id,
            })
        return partners

    def action_withdraw_credits(self, amount=None, method='flow'):
        """
        Retirar créditos de wallet via Flow.cl u otro método
        Flow.cl solo para el retiro — la wallet es interna
        """
        self.ensure_one()
        wallet = self.eco_wallet_id
        if not wallet or wallet.balance <= 0:
            return {'error': 'No credits available'}

        withdraw_amount = amount or wallet.balance
        if withdraw_amount > wallet.balance:
            return {'error': 'Insufficient balance'}

        if method == 'flow':
            # TODO: integrar con Flow.cl para payout real
            return {
                'success': True,
                'amount': withdraw_amount,
                'method': 'flow',
                'message': f'Retiro de {withdraw_amount:.0f} CLP procesado via Flow.cl',
                'pending': True,
            }
        else:
            # Store credit — usar en próxima compra
            wallet.add_transaction(-withdraw_amount, 'withdrawal', 'Store Credit Retired')
            return {
                'success': True,
                'amount': withdraw_amount,
                'method': 'store_credit',
                'new_balance': wallet.balance,
            }


class EcoWallet(models.Model):
    """
    AJUSTE 2: Wallet interna — separada de Flow.cl
    Cada partner tiene una wallet para cashback
    """
    _name = 'eco.wallet'
    _description = 'EcoCupon Wallet'
    _order = 'create_date desc'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.CLP', raise_if_not_found=False))

    # Balance
    balance = fields.Float(compute='_compute_balance', store=True)
    total_earned = fields.Float(compute='_compute_stats')
    total_spent = fields.Float(compute='_compute_stats')
    total_recycled = fields.Integer(compute='_compute_stats')

    # Status
    status = fields.Selection([
        ('active', 'Active'),
        ('frozen', 'Frozen'),
        ('closed', 'Closed'),
    ], default='active')

    transaction_ids = fields.One2many('eco.wallet.transaction', 'wallet_id')

    _sql_constraints = [
        ('partner_unique', 'unique(partner_id)', 'Each partner has one wallet'),
    ]

    @api.depends('transaction_ids.amount', 'transaction_ids.status')
    def _compute_balance(self):
        for wallet in self:
            confirmed = wallet.transaction_ids.filtered(lambda t: t.status == 'confirmed')
            wallet.balance = sum(confirmed.mapped('amount'))
            wallet.total_earned = sum(t.amount for t in confirmed if t.amount > 0)
            wallet.total_spent = abs(sum(t.amount for t in confirmed if t.amount < 0))
            wallet.total_recycled = wallet.transaction_ids.filtered(
                lambda t: t.source == 'recycle' and t.status == 'confirmed'
            ).__len__()

    def add_transaction(self, amount, tx_type, description='', item_id=None, event_id=None):
        """Crear transacción de wallet"""
        self.ensure_one()
        return self.env['eco.wallet.transaction'].create({
            'wallet_id': self.id,
            'partner_id': self.partner_id.id,
            'amount': amount,
            'type': tx_type,
            'description': description,
            'item_id': item_id,
            'event_id': event_id,
            'status': 'confirmed',
        })


class EcoWalletTransaction(models.Model):
    """Cada movimiento en la wallet"""
    _name = 'eco.wallet.transaction'
    _description = 'Wallet Transaction'
    _order = 'create_date desc'

    wallet_id = fields.Many2one('eco.wallet', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', required=True)
    item_id = fields.Many2one('recycle.item', string='Recycle Item')
    event_id = fields.Many2one('recycle.event', string='Recycle Event')
    order_id = fields.Many2one('sale.order', string='Related Order')

    amount = fields.Float(required=True, help='Positivo = crédito, Negativo = débito')
    currency_id = fields.Many2one('res.currency', related='wallet_id.currency_id')

    type = fields.Selection([
        ('credit', 'Credit (Earned)'),
        ('debit', 'Debit (Spent)'),
        ('withdrawal', 'Withdrawal'),
        ('adjustment', 'Manual Adjustment'),
        ('fraud_reversal', 'Fraud Reversal'),
    ], required=True)

    source = fields.Selection([
        ('recycle', 'Recycling Cashback'),
        ('purchase', 'Purchase Bonus'),
        ('referral', 'Referral Bonus'),
        ('promo', 'Promotion'),
        ('withdrawal', 'Withdrawal'),
        ('manual', 'Manual'),
    ], default='recycle')

    description = fields.Char()
    status = fields.Selection([
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('reversed', 'Reversed'),
    ], default='confirmed', required=True)

    # Anti-fraud
    fraud_flag = fields.Boolean(default=False)
    fraud_reason = fields.Char()

    tenant_id = fields.Char(default='ecocupon', index=True)
