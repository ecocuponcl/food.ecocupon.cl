from odoo import models, fields, api
import hashlib
import uuid


class RecycleItem(models.Model):
    """Productos/envases reciclables con QR único"""
    _name = 'recycle.item'
    _description = 'Recyclable Item (QR-linked)'
    _order = 'create_date desc'

    # QR identification
    qr_code = fields.Char(required=True, readonly=True, index=True, copy=False,
                         default=lambda self: self._generate_qr())
    qr_hash = fields.Char(compute='_compute_qr_hash', store=True, index=True)

    # Product linkage
    product_id = fields.Many2one('product.product', string='Product')
    product_name = fields.Char(related='product_id.name', string='Product Name')
    category_id = fields.Many2one('recycle.category', string='Category')

    # Cashback config
    cashback_amount = fields.Float(string='Cashback (CLP)', default=100.0,
                                   help='Amount awarded on successful recycling')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.CLP', raise_if_not_found=False))

    # Status
    status = fields.Selection([
        ('active', 'Active'),
        ('recycled', 'Recycled'),
        ('expired', 'Expired'),
        ('fraud_suspect', 'Fraud Suspect'),
    ], default='active', required=True, index=True)

    # Anti-fraud
    max_scans_per_day = fields.Integer(default=3, help='Max times this QR can be scanned per user per day')
    require_photo = fields.Boolean(default=True)
    require_gps = fields.Boolean(default=False)
    valid_from = fields.Datetime()
    valid_until = fields.Datetime()

    # Tracking
    scan_count = fields.Integer(compute='_compute_scan_count')
    total_cashback_paid = fields.Float(compute='_compute_cashback')
    last_scan_date = fields.Datetime(readonly=True)
    last_scan_partner_id = fields.Many2one('res.partner', readonly=True)

    # Order linkage (where was this item sold)
    order_id = fields.Many2one('sale.order', string='Original Order')
    tenant_id = fields.Char(default='ecocupon', index=True)

    _sql_constraints = [
        ('qr_code_unique', 'unique(qr_code)', 'QR code must be unique'),
    ]

    @api.model
    def _generate_qr(self):
        """Generate unique QR code: ECO-{timestamp}-{random}"""
        import time
        ts = str(int(time.time()))[-6:]
        rand = str(uuid.uuid4())[:6]
        return f"ECO-{ts}-{rand}"

    @api.depends('qr_code')
    def _compute_qr_hash(self):
        for item in self:
            item.qr_hash = hashlib.sha256(item.qr_code.encode()).hexdigest()[:16]

    @api.depends('qr_code')
    def _compute_scan_count(self):
        for item in self:
            item.scan_count = self.env['recycle.event'].search_count([
                ('item_id', '=', item.id),
                ('status', '=', 'validated'),
            ])

    @api.depends('qr_code')
    def _compute_cashback(self):
        for item in self:
            cb = self.env['cashback.transaction'].search([
                ('item_id', '=', item.id),
                ('status', '=', 'paid'),
            ])
            item.total_cashback_paid = sum(cb.mapped('amount'))

    def action_validate_fraud(self):
        """Anti-fraud checks before approving a scan"""
        self.ensure_one()
        partner = self.env.user.partner_id if self.env.user.partner_id.id > 1 else None
        if not partner:
            return {'fraud': False, 'reason': 'anonymous', 'score': 0}

        today = fields.Date.today()
        scans_today = self.env['recycle.event'].search_count([
            ('item_id', '=', self.id),
            ('partner_id', '=', partner.id),
            ('create_date', '>=', fields.Datetime.to_string(fields.Datetime.today().replace(hour=0, minute=0, second=0))),
            ('status', 'in', ['pending', 'validated']),
        ])

        fraud_checks = {
            'max_scans_exceeded': scans_today >= self.max_scans_per_day,
            'already_recycled': self.status == 'recycled',
            'expired': self.valid_until and self.valid_until < fields.Datetime.now(),
            'not_started': self.valid_from and self.valid_from > fields.Datetime.now(),
        }

        fraud_score = sum(1 for v in fraud_checks.values() if v)
        reason = ', '.join(k for k, v in fraud_checks.items() if v) or 'ok'

        return {
            'fraud': fraud_score > 0,
            'score': fraud_score,
            'reason': reason,
            'scans_today': scans_today,
            'checks': fraud_checks,
        }

    def action_mark_recycled(self, partner_id=None, photo=None, gps_lat=None, gps_lon=None):
        """Mark item as recycled after validation"""
        self.ensure_one()

        # Run fraud check
        fraud_result = self.action_validate_fraud()
        if fraud_result.get('fraud'):
            self.status = 'fraud_suspect'
            return {'success': False, 'reason': fraud_result['reason'], 'fraud': True}

        # Create event
        event = self.env['recycle.event'].create({
            'item_id': self.id,
            'partner_id': partner_id,
            'type': 'recycle',
            'status': 'validated',
            'photo_url': photo,
            'gps_lat': gps_lat,
            'gps_lon': gps_lon,
            'cashback_amount': self.cashback_amount,
        })

        # Create cashback transaction
        if partner_id:
            self.env['cashback.transaction'].create({
                'partner_id': partner_id,
                'item_id': self.id,
                'event_id': event.id,
                'amount': self.cashback_amount,
                'currency_id': self.currency_id.id,
                'status': 'paid',
                'source': 'recycle',
            })
            partner = self.env['res.partner'].browse(partner_id)
            partner.recycle_credits += self.cashback_amount
            partner.recycle_count += 1

        self.status = 'recycled'
        self.last_scan_date = fields.Datetime.now()
        self.last_scan_partner_id = partner_id

        return {'success': True, 'cashback': self.cashback_amount, 'event_id': event.id}
