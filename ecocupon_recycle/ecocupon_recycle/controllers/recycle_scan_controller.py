from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class RecycleScanController(http.Controller):

    @http.route('/kiosk/scan_qr', type='json', auth='public')
    def scan_qr(self, qr_code=None, photo_url=None, gps_lat=None, gps_lon=None, **kw):
        """
        Scan QR code → validate → cashback
        Called from kiosk UI or mobile app
        """
        _logger.info(f"Recycle scan: qr={qr_code}, photo={bool(photo_url)}, gps=({gps_lat},{gps_lon})")

        if not qr_code:
            return {'error': 'No QR code provided'}

        # Get partner (logged in user or anonymous)
        partner = None
        if request.env.user and request.env.user.partner_id.id > 1:
            partner = request.env.user.partner_id

        # Anti-fraud: collect evidence
        ip = request.httprequest.remote_addr
        ua = request.httprequest.user_agent.string if request.httprequest.user_agent else ''

        # Process scan
        result = request.env['recycle.event'].create_from_scan(
            qr_code=qr_code,
            partner_id=partner.id if partner else None,
            photo=photo_url,
            gps=(gps_lat, gps_lon) if gps_lat and gps_lon else None,
            ip=ip,
            ua=ua,
        )

        return result

    @http.route('/kiosk/recycle_status', type='json', auth='public')
    def recycle_status(self, **kw):
        """Get user's recycle stats"""
        partner = request.env.user.partner_id if request.env.user and request.env.user.partner_id.id > 1 else None
        if not partner:
            return {'credits': 0, 'count': 0, 'history': []}

        return {
            'credits': partner.recycle_credits,
            'count': partner.recycle_count,
            'qr_code': partner.recycle_qr_code,
            'history': request.env['cashback.transaction'].sudo().search_read(
                [('partner_id', '=', partner.id)],
                ['amount', 'status', 'source', 'create_date'],
                order='create_date desc',
                limit=10,
            ),
        }

    @http.route('/kiosk/recycle', type='http', auth='public', website=True)
    def recycle_page(self, **kw):
        """Recycle scan page"""
        partner = request.env.user.partner_id if request.env.user and request.env.user.partner_id.id > 1 else None
        return request.render('ecocupon_recycle.recycle_scan_page', {
            'partner': partner,
            'credits': partner.recycle_credits if partner else 0,
        })

    @http.route('/kiosk/admin/validate_recycle', type='json', auth='user')
    def admin_validate(self, event_id, action='approve', **kw):
        """Admin manual validation"""
        event = request.env['recycle.event'].sudo().browse(event_id)
        if not event:
            return {'error': 'Event not found'}

        if action == 'approve':
            item = event.item_id
            item.action_mark_recycled(
                partner_id=event.partner_id.id if event.partner_id else None,
                photo=event.photo_url,
            )
            return {'success': True, 'message': 'Approved'}
        elif action == 'reject':
            event.status = 'rejected'
            return {'success': True, 'message': 'Rejected'}

        return {'error': 'Invalid action'}
