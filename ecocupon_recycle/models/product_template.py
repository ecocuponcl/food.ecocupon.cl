from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Recycling config
    is_recyclable = fields.Boolean(string='Recyclable', default=True)
    recycle_category_id = fields.Many2one('recycle.category', string='Recycle Category')
    recycle_cashback = fields.Float(string='Recycle Cashback (CLP)', default=100.0,
                                     help='Cashback awarded when customer recycles this product')
    recycle_qr_enabled = fields.Boolean(string='Generate QR on Sale', default=True)

    def action_generate_qr_items(self, quantity=1):
        """Generate QR items for this product (e.g., when ordering stock)"""
        self.ensure_one()
        RecycleItem = self.env['recycle.item']
        items = RecycleItem
        for i in range(quantity):
            item = RecycleItem.create({
                'product_id': self.product_variant_id.id,
                'category_id': self.recycle_category_id.id,
                'cashback_amount': self.recycle_cashback,
                'require_photo': True,
            })
            items |= item
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'QR Items Generated',
                'message': f'{quantity} QR codes created for {self.name}',
                'type': 'success',
                'sticky': False,
            }
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Recycling config (variant level)
    is_recyclable = fields.Boolean(related='product_tmpl_id.is_recyclable', readonly=False)
    recycle_cashback = fields.Float(related='product_tmpl_id.recycle_cashback', readonly=False)
