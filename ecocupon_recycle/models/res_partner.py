"""
ResPartner extends con recycle info
La wallet se crea automáticamente en eco_wallet.py
"""
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Recycling tracking (redundante con wallet pero útil para quick access)
    recycle_count = fields.Integer(string='Items Recycled', default=0)
    recycle_qr_code = fields.Char(string='Personal QR Code', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        for partner in partners:
            if not partner.recycle_qr_code:
                partner.recycle_qr_code = f"USER-{partner.id:06d}"
        return partners
