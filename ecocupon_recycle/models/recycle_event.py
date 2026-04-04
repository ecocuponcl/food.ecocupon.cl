from odoo import models, fields, api
import logging

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
        ('recycle', 'Recycle Validated'),
        ('reject', 'Rejected'),
        ('photo', 'Photo Uploaded'),
        ('truck_pickup', 'Truck Pickup'),
    ], required=True, default='scan')

    status = fields.Selection([
        ('pending', 'Pending Review'),
        ('validated', 'Validated'),
        ('rejected', 'Rejected'),
        ('fraud', 'Fraud Detected'),
    ], default='pending', required=True, index=True)

    # Anti-fraud evidence
    photo_url = fields.Char()
    gps_lat = fields.Float()
    gps_lon = fields.Float()
    ip_address = fields.Char()
    user_agent = fields.Char()
    device_fingerprint = fields.Char()

    # Validation
    validated_by = fields.Many2one('res.users', string='Validated By')
    validation_method = fields.Selection([
        ('auto', 'Automatic'),
        ('photo', 'Photo Review'),
        ('gps', 'GPS Zone'),
        ('truck', 'Truck Pickup'),
        ('manual', 'Manual Override'),
    ], default='auto')

    validation_score = fields.Float(default=0.0, help='AI/Rule validation score 0-1')

    # Cashback
    cashback_amount = fields.Float()

    # Sync
    synced_to_supabase = fields.Boolean(default=False)
    tenant_id = fields.Char(default='ecocupon', index=True)

    @api.model
    def create_from_scan(self, qr_code, partner_id=None, photo=None, gps=None, ip=None, ua=None):
        """Create event from QR scan with anti-fraud checks"""
        item = self.env['recycle.item'].search([('qr_code', '=', qr_code)], limit=1)
        if not item:
            return {'error': 'QR not found', 'qr_code': qr_code}

        fraud = item.action_validate_fraud()
        if fraud.get('fraud'):
            event = self.create({
                'item_id': item.id,
                'partner_id': partner_id,
                'type': 'scan',
                'status': 'fraud',
                'validation_score': 0.0,
                'ip_address': ip,
                'user_agent': ua,
            })
            return {
                'error': 'Fraud detected',
                'reason': fraud['reason'],
                'score': fraud['score'],
                'event_id': event.id,
            }

        # Auto-validate if conditions met
        auto_approve = not item.require_photo or photo
        if gps:
            auto_approve = True  # GPS validation counts

        if auto_approve:
            result = item.action_mark_recycled(
                partner_id=partner_id,
                photo=photo,
                gps_lat=gps[0] if gps else None,
                gps_lon=gps[1] if gps else None,
            )
            return {
                'success': True,
                'cashback': result.get('cashback', 0),
                'item_name': item.product_name or item.category_id.name or 'Item',
                'status': 'validated',
            }

        # Pending review
        event = self.create({
            'item_id': item.id,
            'partner_id': partner_id,
            'type': 'scan',
            'status': 'pending',
            'photo_url': photo,
            'gps_lat': gps[0] if gps else None,
            'gps_lon': gps[1] if gps else None,
            'ip_address': ip,
            'user_agent': ua,
        })
        return {
            'pending': True,
            'event_id': event.id,
            'message': 'Reciclaje registrado. Recompensa pendiente de validación.',
        }
