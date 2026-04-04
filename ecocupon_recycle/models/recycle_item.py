"""
AJUSTE 1: QR fuerte — order linkage, expiration, status, unique hash
AJUSTE 3: Image hash para detección de duplicados
"""
from odoo import models, fields, api
import hashlib
import uuid
import time


class RecycleItem(models.Model):
    """Envase reciclable con QR único vinculado a compra real"""
    _name = 'recycle.item'
    _description = 'Recyclable Item (QR-linked to purchase)'
    _order = 'create_date desc'

    # ═══ QR FUERTE (AJUSTE 1) ═══
    qr_code = fields.Char(required=True, readonly=True, index=True, copy=False,
                         default=lambda self: self._generate_qr())
    qr_hash = fields.Char(compute='_compute_qr_hash', store=True, index=True,
                         help='SHA256 del QR para verificación criptográfica')
    qr_signature = fields.Char(readonly=True, copy=False,
                              help='Firma HMAC del QR para validar autenticidad')

    # ═══ VINCULACIÓN A COMPRA REAL ═══
    order_id = fields.Many2one('sale.order', string='Original Order', required=False,
                              help='La compra que generó este envase')
    order_ref = fields.Char(related='order_id.client_order_ref', string='Order Ref')
    product_id = fields.Many2one('product.product', string='Product')
    product_name = fields.Char(related='product_id.name', string='Product Name')
    category_id = fields.Many2one('recycle.category', string='Category')

    # ═══ ESTADO DEL ENVASE ═══
    status = fields.Selection([
        ('issued', 'Issued (sold)'),
        ('scanned', 'Scanned (pending validation)'),
        ('validated', 'Validated (recycling confirmed)'),
        ('cashback_paid', 'Cashback Paid'),
        ('expired', 'Expired'),
        ('fraud_flagged', 'Fraud Flagged'),
    ], default='issued', required=True, index=True)

    # ═══ TIMESTAMPS CRÍTICOS ═══
    issued_at = fields.Datetime(string='Issued At', default=fields.Datetime.now,
                               required=True, help='Cuando se vendió el producto')
    expires_at = fields.Datetime(string='Expires At',
                                help='Ventana máxima para reciclar (default: 30 días)')
    first_scanned_at = fields.Datetime(readonly=True)
    validated_at = fields.Datetime(readonly=True)
    cashback_paid_at = fields.Datetime(readonly=True)

    # ═══ CASHBACK CONFIG ═══
    cashback_amount = fields.Float(string='Cashback (CLP)', default=100.0)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.CLP', raise_if_not_found=False))

    # ═══ ANTI-FRAUD ═══
    max_scans = fields.Integer(default=1, help='QR de un solo uso')
    require_photo = fields.Boolean(default=True)
    require_gps = fields.Boolean(default=False)
    min_delay_hours = fields.Float(default=1.0, help='Horas mínimas entre compra y reciclaje')
    image_hash = fields.Char(readonly=True, help='Hash de la foto para detectar duplicados')

    # ═══ TRACKING ═══
    scan_count = fields.Integer(compute='_compute_stats')
    scan_partner_id = fields.Many2one('res.partner', readonly=True)
    validation_method = fields.Selection([
        ('photo', 'Photo Only'),
        ('gps', 'GPS Zone'),
        ('truck', 'Truck Pickup'),
        ('hybrid', 'Hybrid (Photo + GPS)'),
    ], readonly=True)

    tenant_id = fields.Char(default='ecocupon', index=True)

    _sql_constraints = [
        ('qr_code_unique', 'unique(qr_code)', 'QR code must be unique'),
    ]

    @api.model
    def _generate_qr(self):
        """
        QR fuerte: ECO-{timestamp6}-{uuid6}
        Ejemplo: ECO-260404-a3f2b1
        """
        ts = fields.Datetime.now().strftime('%y%m%d')[2:] + fields.Datetime.now().strftime('%H%M')[:4]
        rand = str(uuid.uuid4())[:6]
        return f"ECO-{ts}-{rand}"

    @api.depends('qr_code')
    def _compute_qr_hash(self):
        for item in self:
            item.qr_hash = hashlib.sha256(item.qr_code.encode()).hexdigest()[:16]

    @api.model_create_multi
    def create(self, vals_list):
        """Generar firma HMAC al crear"""
        items = super().create(vals_list)
        for item in items:
            # Firma: HMAC-SHA256 del qr_code + secret del sistema
            secret = self.env['ir.config_parameter'].sudo().get_param('ecocupon.qr_secret', 'eco-secret-default')
            item.qr_signature = hmac.new(
                secret.encode(),
                f"{item.qr_code}:{item.order_id.id}:{item.product_id.id}".encode(),
                hashlib.sha256
            ).hexdigest()[:16]

            # Default expiry: 30 days
            if not item.expires_at:
                from datetime import timedelta
                item.expires_at = item.issued_at + timedelta(days=30)
        return items

    def _compute_stats(self):
        for item in self:
            item.scan_count = self.env['recycle.event'].search_count([
                ('item_id', '=', item.id),
            ])

    def action_verify_qr_authenticity(self, qr_code):
        """
        Verificar que un QR es auténtico y válido para escanear
        AJUSTE 1 + 3: Validación fuerte
        """
        item = self.search([('qr_code', '=', qr_code)], limit=1)
        if not item:
            return {'valid': False, 'reason': 'qr_not_found', 'message': 'Código QR no encontrado'}

        now = fields.Datetime.now()

        # Check 1: Estado
        if item.status in ('validated', 'cashback_paid'):
            return {'valid': False, 'reason': 'already_recycled', 'message': 'Este envase ya fue reciclado'}
        if item.status == 'expired':
            return {'valid': False, 'reason': 'expired', 'message': 'Código QR expirado'}
        if item.status == 'fraud_flagged':
            return {'valid': False, 'reason': 'fraud', 'message': 'Este QR fue marcado como fraude'}

        # Check 2: Expiración
        if item.expires_at and item.expires_at < now:
            item.status = 'expired'
            return {'valid': False, 'reason': 'expired', 'message': 'Ventana de reciclaje expirada'}

        # Check 3: Delay mínimo (no reciclar inmediatamente después de comprar)
        if item.min_delay_hours > 0 and item.issued_at:
            from datetime import timedelta
            min_recycle_time = item.issued_at + timedelta(hours=item.min_delay_hours)
            if now < min_recycle_time:
                remaining = min_recycle_time - now
                return {
                    'valid': False,
                    'reason': 'too_soon',
                    'message': f'Debe esperar {item.min_delay_hours:.0f}h desde la compra',
                    'retry_after': min_recycle_time.isoformat(),
                }

        # Check 4: Max scans
        if item.scan_count >= item.max_scans:
            return {'valid': False, 'reason': 'max_scans', 'message': 'QR ya utilizado'}

        return {
            'valid': True,
            'item_id': item.id,
            'product_name': item.product_name or 'Producto',
            'category': item.category_id.name if item.category_id else '',
            'cashback': item.cashback_amount,
            'issued_at': item.issued_at.isoformat(),
            'status': item.status,
        }

    def action_mark_scanned(self, partner_id=None, photo_url=None, gps=None, image_hash=None):
        """
        AJUSTE 3 + 5: Marcar como escaneado → pendiente validación
        NO paga cashback directo — requiere evento validado
        """
        self.ensure_one()

        # Verify authenticity first
        verify = self.action_verify_qr_authenticity(self.qr_code)
        if not verify['valid']:
            return {'success': False, 'reason': verify['reason'], 'message': verify['message']}

        # Create scan event (pending validation)
        event = self.env['recycle.event'].create({
            'item_id': self.id,
            'partner_id': partner_id,
            'order_id': self.order_id.id,
            'type': 'scan',
            'status': 'pending',
            'photo_url': photo_url,
            'image_hash': image_hash,
            'gps_lat': gps[0] if gps else None,
            'gps_lon': gps[1] if gps else None,
            'cashback_amount': self.cashback_amount,
            'validation_method': 'photo' if photo_url else ('gps' if gps else 'scan'),
        })

        self.status = 'scanned'
        self.first_scanned_at = fields.Datetime.now()
        self.scan_partner_id = partner_id
        if image_hash:
            self.image_hash = image_hash

        return {
            'success': True,
            'pending': True,
            'event_id': event.id,
            'message': 'Escaneo registrado. Cashback pendiente de validación.',
            'product_name': verify.get('product_name', ''),
            'cashback': self.cashback_amount,
        }

    def action_validate_and_pay(self, validation_method='auto'):
        """
        AJUSTE 5: Evento validado → pago (no foto → pago)
        Solo se ejecuta cuando hay confirmación (camión, punto, admin)
        """
        self.ensure_one()

        if self.status not in ('scanned',):
            return {'success': False, 'reason': 'invalid_status', 'message': f'Estado actual: {self.status}'}

        # Check for duplicate image hash (AJUSTE 3)
        if self.image_hash:
            dup = self.search([
                ('image_hash', '=', self.image_hash),
                ('id', '!=', self.id),
                ('status', 'in', ('validated', 'cashback_paid')),
            ], limit=1)
            if dup:
                self.status = 'fraud_flagged'
                return {'success': False, 'reason': 'duplicate_photo', 'message': 'Foto duplicada detectada'}

        # Mark validated
        self.status = 'validated'
        self.validated_at = fields.Datetime.now()
        self.validation_method = validation_method

        # Find pending event and approve
        event = self.env['recycle.event'].search([
            ('item_id', '=', self.id),
            ('status', '=', 'pending'),
        ], order='create_date desc', limit=1)

        if event:
            event.status = 'validated'
            event.validated_by = self.env.user

        # Create cashback transaction (wallet internal, not Flow)
        if self.scan_partner_id:
            tx = self.env['eco.wallet.transaction'].create({
                'wallet_id': self.scan_partner_id.eco_wallet_id.id if self.scan_partner_id.eco_wallet_id else None,
                'partner_id': self.scan_partner_id.id,
                'item_id': self.id,
                'event_id': event.id,
                'amount': self.cashback_amount,
                'type': 'credit',
                'source': 'recycle',
                'status': 'confirmed',
            })
            self.status = 'cashback_paid'
            self.cashback_paid_at = fields.Datetime.now()

            return {
                'success': True,
                'cashback': self.cashback_amount,
                'transaction_id': tx.id,
                'wallet_balance': tx.wallet_id.balance if tx.wallet_id else 0,
                'message': f'{self.cashback_amount:.0f} CLP acreditados en wallet',
            }

        return {'success': True, 'message': 'Validado sin partner asociado'}


import hmac as hmac_module
