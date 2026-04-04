"""
AJUSTE 3 + 4 + 5: Endpoints optimizados
- scan_qr: registra → pendiente (no paga directo)
- confirm: camión/punto valida → cashback
- wallet: consulta saldo
"""
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class RecycleScanController(http.Controller):

    @http.route('/kiosk/scan_qr', type='json', auth='public')
    def scan_qr(self, qr_code=None, photo_url=None, gps_lat=None, gps_lon=None,
                image_hash=None, **kw):
        """
        AJUSTE 3 + 5: Escanear QR → registrar evento → PENDIENTE validación
        NO paga cashback directo — requiere validación (foto/GPS/camión)
        """
        _logger.info(f"Recycle scan: qr={qr_code}, photo={bool(photo_url)}, gps=({gps_lat},{gps_lon}), hash={bool(image_hash)}")

        if not qr_code:
            return {'error': 'No QR code provided'}

        # Get partner
        partner = None
        if request.env.user and request.env.user.partner_id.id > 1:
            partner = request.env.user.partner_id

        # Evidence collection
        ip = request.httprequest.remote_addr
        ua = request.httprequest.user_agent.string if request.httprequest.user_agent else ''

        # Process scan (AJUSTE 3: validation hybrid)
        result = request.env['recycle.event'].create_from_scan(
            qr_code=qr_code,
            partner_id=partner.id if partner else None,
            photo_url=photo_url,
            gps=(float(gps_lat), float(gps_lon)) if gps_lat and gps_lon else None,
            ip=ip,
            ua=ua,
            image_hash=image_hash,
        )

        return result

    @http.route('/kiosk/verify_qr', type='json', auth='public')
    def verify_qr(self, qr_code=None, **kw):
        """
        AJUSTE 1: Solo verificar QR — sin registrar scan
        Útil para preview antes de escanear
        """
        if not qr_code:
            return {'valid': False, 'reason': 'no_qr'}

        item = request.env['recycle.item'].sudo().search([('qr_code', '=', qr_code)], limit=1)
        if not item:
            return {'valid': False, 'reason': 'not_found', 'message': 'QR no encontrado'}

        return item.action_verify_qr_authenticity(qr_code)

    @http.route('/kiosk/recycle/confirm', type='json', auth='user')
    def confirm_recycle(self, event_ids=None, method='manual', **kw):
        """
        AJUSTE 4: Confirmar validación de reciclaje
        Usado por admin/camión para aprobar pendientes
        """
        if not event_ids:
            return {'error': 'No event IDs provided'}

        events = request.env['recycle.event'].sudo().browse(event_ids)
        results = []
        for event in events:
            if event.status == 'pending':
                event.action_validate(method=method)
                results.append({
                    'event_id': event.id,
                    'status': 'validated',
                    'cashback': event.cashback_amount,
                })
            else:
                results.append({
                    'event_id': event.id,
                    'status': event.status,
                    'message': 'Already processed',
                })

        return {'confirmed': results}

    @http.route('/kiosk/recycle/truck_confirm', type='json', auth='user')
    def truck_confirm(self, truck_id=None, qr_codes=None, **kw):
        """
        AJUSTE 4: Camión confirma recogida → cashback pagado
        """
        if not qr_codes:
            return {'error': 'No QR codes provided'}

        truck = request.env['recycle.truck'].sudo().browse(truck_id) if truck_id else None
        result = truck.action_confirm_pickup(qr_codes) if truck else {
            'total': 0,
            'error': 'No truck specified',
        }

        return result

    @http.route('/kiosk/recycle/wallet', type='json', auth='public')
    def wallet_status(self, **kw):
        """
        AJUSTE 2: Consultar wallet interna
        """
        partner = request.env.user.partner_id if request.env.user and request.env.user.partner_id.id > 1 else None
        if not partner:
            return {'error': 'Not authenticated'}

        wallet = partner.eco_wallet_id
        if not wallet:
            return {'balance': 0, 'total_earned': 0, 'total_spent': 0, 'total_recycled': 0}

        return {
            'balance': wallet.balance,
            'total_earned': wallet.total_earned,
            'total_spent': wallet.total_spent,
            'total_recycled': wallet.total_recycled,
            'status': wallet.status,
            'recent_transactions': [
                {
                    'amount': t.amount,
                    'type': t.type,
                    'source': t.source,
                    'description': t.description,
                    'date': t.create_date.isoformat(),
                }
                for t in wallet.transaction_ids[:10]
            ],
        }

    @http.route('/kiosk/recycle/withdraw', type='json', auth='public')
    def withdraw_credits(self, amount=None, method='flow', **kw):
        """
        AJUSTE 2: Retirar créditos de wallet
        Flow.cl solo para payout — wallet es interna
        """
        partner = request.env.user.partner_id if request.env.user and request.env.user.partner_id.id > 1 else None
        if not partner:
            return {'error': 'Not authenticated'}

        result = partner.action_withdraw_credits(amount=amount, method=method)
        return result

    @http.route('/kiosk/recycle', type='http', auth='public', website=True)
    def recycle_page(self, **kw):
        """Recycle scan page"""
        partner = request.env.user.partner_id if request.env.user and request.env.user.partner_id.id > 1 else None
        wallet = partner.eco_wallet_id if partner else None
        return request.render('ecocupon_recycle.recycle_scan_page', {
            'partner': partner,
            'balance': wallet.balance if wallet else 0,
            'total_recycled': wallet.total_recycled if wallet else 0,
        })

    @http.route('/kiosk/admin/validate_recycle', type='json', auth='user')
    def admin_validate(self, event_id, action='approve', **kw):
        """Admin manual validation"""
        event = request.env['recycle.event'].sudo().browse(event_id)
        if not event:
            return {'error': 'Event not found'}

        if action == 'approve':
            event.action_validate(method='manual')
            return {'success': True, 'message': 'Approved'}
        elif action == 'reject':
            event.action_reject(reason='Manual rejection')
            return {'success': True, 'message': 'Rejected'}

        return {'error': 'Invalid action'}
