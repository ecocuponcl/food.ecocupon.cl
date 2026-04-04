from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Recycling tracking
    recycle_credits = fields.Float(string='Recycle Credits (CLP)', default=0.0,
                                   help='Accumulated cashback credits from recycling')
    recycle_count = fields.Integer(string='Items Recycled', default=0)
    recycle_qr_code = fields.Char(string='Personal QR Code', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        for partner in partners:
            if not partner.recycle_qr_code:
                partner.recycle_qr_code = f"USER-{partner.id:06d}"
        return partners

    def action_redeem_credits(self):
        """Redeem credits via Flow.cl or store credit"""
        self.ensure_one()
        if self.recycle_credits <= 0:
            return {'error': 'No credits available'}

        # TODO: integrate with Flow.cl payout or store credit system
        return {
            'success': True,
            'amount': self.recycle_credits,
            'message': f'{self.recycle_credits:.0f} CLP redeemados',
        }
