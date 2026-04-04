"""
AJUSTE 3: Validación híbrida — image hash, GPS, timestamp
AJUSTE 4: Evento confirm endpoint para camión/punto físico
AJUSTE 5: Evento validado → pago (no directo)
"""
from odoo import models, fields, api
import logging
import hashlib

_logger = logging.getLogger(__name__)


class RecycleEvent(models.Model):
    """Cada escaneo/validación de reciclaje"""
    _name = 'recycle.event'
    _description = 'Recycle Scan Event'
    _order = 'create_date desc'

    item_id = fields.Many2one('recycle.item', string='Item', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Customer')
    order_id = fields.Many2one('sale.order', string='Related Order')

    type = fields.Selection([
        ('scan', 'QR Scan'),
        ('photo_upload', 'Photo Uploaded'),
        ('gps_check', 'GPS Zone Check'),
        ('truck_pickup', 'Truck Pickup'),
        ('validated', 'Validated'),
        ('rejected', 'Rejected'),
    ], required=True, default='scan')

    status = fields.Selection([
        ('pending', 'Pending Validation'),
        ('validated', 'Validated'),
        ('rejected', 'Rejected'),
        ('fraud', 'Fraud Detected'),
    ], default='pending', required=True, index=True)

    # ═══ EVIDENCIA ANTI-FRAUD ═══
    photo_url = fields.Char()
    image_hash = fields.Char(index=True, help='SHA256 hash de la foto para detectar duplicados')
    gps_lat = fields.Float()
    gps_lon = fields.Float()
    gps_accuracy = fields.Float(help='GPS accuracy in meters')
    ip_address = fields.Char()
    user_agent = fields.Char()
    device_fingerprint = fields.Char()

    # ═══ VALIDACIÓN ═══
    validated_by = fields.Many2one('res.users', string='Validated By')
    validation_method = fields.Selection([
        ('auto', 'Automatic (Photo)'),
        ('gps', 'GPS Zone Validation'),
        ('truck', 'Truck/Physical Pickup'),
        ('hybrid', 'Hybrid (Photo + GPS)'),
        ('manual', 'Manual Override'),
    ], default='auto')

    validation_score = fields.Float(default=0.0, help='AI/Rule validation score 0-1')
    validated_at = fields.Datetime()

    # Cashback
    cashback_amount = fields.Float()

    # ═══ FUENTE DE VALIDACIÓN ═══
    validation_source = fields.Selection([
        ('customer', 'Customer Scan'),
        ('truck', 'Truck/Driver'),
        ('drop_point', 'Drop-off Point'),
        ('admin', 'Admin Manual'),
    ], default='customer')

    truck_id = fields.Many2one('recycle.truck', string='Validating Truck')
    drop_point_id = fields.Many2one('recycle.drop_point', string='Drop-off Point')

    tenant_id = fields.Char(default='ecocupon', index=True)

    @api.model
    def compute_image_hash(self, photo_data):
        """
        AJUSTE 3: Hash SHA256 de imagen para detectar fotos duplicadas
        """
        if not photo_data:
            return None
        return hashlib.sha256(photo_data).hexdigest()[:32]

    @api.model
    def check_duplicate_photo(self, image_hash):
        """Verificar si la foto ya fue usada en otro reciclaje"""
        if not image_hash:
            return None
        return self.search([
            ('image_hash', '=', image_hash),
            ('status', '=', 'validated'),
        ], limit=1)

    @api.model
    def create_from_scan(self, qr_code, partner_id=None, photo_url=None,
                         gps=None, ip=None, ua=None, image_hash=None):
        """
        AJUSTE 3 + 5: Crear evento de scan con validación híbrida
        NO paga cashback — solo registra el evento pendiente
        """
        # Find item
        item = self.env['recycle.item'].search([('qr_code', '=', qr_code)], limit=1)
        if not item:
            return {'error': 'QR not found', 'qr_code': qr_code}

        # Verify QR authenticity
        verify = item.action_verify_qr_authenticity(qr_code)
        if not verify['valid']:
            # Log fraud attempt
            self.create({
                'item_id': item.id,
                'partner_id': partner_id,
                'type': 'scan',
                'status': 'fraud',
                'validation_score': 0.0,
                'ip_address': ip,
                'user_agent': ua,
                'image_hash': image_hash,
            })
            return {
                'error': verify['message'],
                'reason': verify['reason'],
                'fraud': True,
            }

        # Check for duplicate photo (AJUSTE 3)
        if image_hash:
            dup_event = self.check_duplicate_photo(image_hash)
            if dup_event:
                item.status = 'fraud_flagged'
                self.create({
                    'item_id': item.id,
                    'partner_id': partner_id,
                    'type': 'photo_upload',
                    'status': 'fraud',
                    'image_hash': image_hash,
                    'validation_score': 0.0,
                    'fraud_flag': True,
                })
                return {
                    'error': 'Foto duplicada detectada',
                    'reason': 'duplicate_photo',
                    'fraud': True,
                }

        # Determine validation method
        has_photo = bool(photo_url)
        has_gps = gps is not None

        if has_photo and has_gps:
            val_method = 'hybrid'
            val_score = 0.9  # High confidence
        elif has_gps:
            val_method = 'gps'
            val_score = 0.8
        elif has_photo:
            val_method = 'auto'
            val_score = 0.6
        else:
            val_method = 'auto'
            val_score = 0.4

        # Auto-validate if score is high enough AND all requirements met
        auto_approve = val_score >= 0.8 and (
            (item.require_photo and has_photo) or not item.require_photo
        ) and (
            (item.require_gps and has_gps) or not item.require_gps
        )

        if auto_approve:
            # AJUSTE 5: Validado → pagar cashback via wallet
            result = item.action_validate_and_pay(validation_method=val_method)
            return {
                'success': True,
                'validated': True,
                'cashback': result.get('cashback', item.cashback_amount),
                'wallet_balance': result.get('wallet_balance', 0),
                'item_name': item.product_name or item.category_id.name or 'Item',
                'status': 'validated',
                'validation_method': val_method,
            }

        # Otherwise: pending validation (photo review or truck confirmation)
        event = self.create({
            'item_id': item.id,
            'partner_id': partner_id,
            'order_id': item.order_id.id if item.order_id else None,
            'type': 'photo_upload' if has_photo else ('gps_check' if has_gps else 'scan'),
            'status': 'pending',
            'photo_url': photo_url,
            'image_hash': image_hash,
            'gps_lat': gps[0] if gps else None,
            'gps_lon': gps[1] if gps else None,
            'ip_address': ip,
            'user_agent': ua,
            'validation_method': val_method,
            'validation_score': val_score,
            'cashback_amount': item.cashback_amount,
        })

        # Mark item as scanned
        item.action_mark_scanned(
            partner_id=partner_id,
            photo_url=photo_url,
            gps=gps,
            image_hash=image_hash,
        )

        return {
            'pending': True,
            'event_id': event.id,
            'score': val_score,
            'message': 'Reciclaje registrado. Pendiente de validación.',
            'product_name': item.product_name or item.category_id.name or 'Item',
        }

    def action_validate(self, method='manual'):
        """Validar evento pendiente → pagar cashback"""
        for event in self:
            if event.status != 'pending':
                continue

            # Check for duplicate image
            if event.image_hash:
                dup = self.check_duplicate_photo(event.image_hash)
                if dup and dup.id != event.id:
                    event.status = 'fraud'
                    event.item_id.status = 'fraud_flagged'
                    continue

            event.status = 'validated'
            event.validation_method = method
            event.validated_at = fields.Datetime.now()
            event.validated_by = self.env.user

            # Pay cashback via wallet
            event.item_id.action_validate_and_pay(validation_method=method)

    def action_reject(self, reason=''):
        for event in self:
            event.status = 'rejected'
            event.item_id.status = 'issued'  # Reset for re-scan


class RecycleTruck(models.Model):
    """
    AJUSTE 4: Camiones/puntos de reciclaje físico
    Validación en el mundo real
    """
    _name = 'recycle.truck'
    _description = 'Recycle Truck / Pickup Vehicle'

    name = fields.Char(required=True)
    plate = fields.Char(string='License Plate')
    driver_id = fields.Many2one('res.partner', string='Driver')
    active = fields.Boolean(default=True)

    def action_confirm_pickup(self, qr_codes):
        """
        AJUSTE 4: Camión confirma recogida de envases
        → cashback confirmado
        """
        items = self.env['recycle.item'].search([
            ('qr_code', 'in', qr_codes),
            ('status', 'in', ('scanned', 'issued')),
        ])

        confirmed = []
        for item in items:
            result = item.action_validate_and_pay(validation_method='truck')
            if result.get('success'):
                confirmed.append({
                    'qr_code': item.qr_code,
                    'cashback': result.get('cashback', 0),
                    'wallet_balance': result.get('wallet_balance', 0),
                })

                # Create truck validation event
                self.env['recycle.event'].create({
                    'item_id': item.id,
                    'partner_id': item.scan_partner_id.id,
                    'order_id': item.order_id.id if item.order_id else None,
                    'type': 'truck_pickup',
                    'status': 'validated',
                    'validation_method': 'truck',
                    'validation_source': 'truck',
                    'truck_id': self.id,
                    'cashback_amount': item.cashback_amount,
                    'validated_by': self.env.user,
                })

        return {
            'total': len(confirmed),
            'cashback_paid': sum(c['cashback'] for c in confirmed),
            'items': confirmed,
        }


class RecycleDropPoint(models.Model):
    """Punto físico de reciclaje"""
    _name = 'recycle.drop_point'
    _description = 'Recycle Drop-off Point'

    name = fields.Char(required=True)
    address = fields.Char()
    gps_lat = fields.Float()
    gps_lon = fields.Float()
    radius_meters = fields.Float(default=100.0, help='GPS validation radius')
    active = fields.Boolean(default=True)

    def validate_gps(self, lat, lon):
        """Check if GPS coordinates are within this drop point"""
        import math
        if not self.gps_lat or not self.gps_lon:
            return False
        # Simple Haversine approximation
        dlat = lat - self.gps_lat
        dlon = lon - self.gps_lon
        distance = math.sqrt(dlat**2 + dlon**2) * 111000  # Rough meters
        return distance <= self.radius_meters
