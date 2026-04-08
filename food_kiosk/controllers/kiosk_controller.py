from odoo import http
from odoo.http import request
import os
import requests
import logging

_logger = logging.getLogger(__name__)

# Agent URL — local Docker service (falls back to external if needed)
AGENT_URL = os.environ.get("FOOD_AGENT_URL", "http://agent:9000")


class FoodKioskController(http.Controller):

    @http.route('/', type='http', auth='public', website=True)
    def landing(self, **kw):
        """Landing page — entry point with CTA to kiosk"""
        products = request.env['product.product'].sudo().search([
            ('type', '=', 'consu'),
            ('sale_ok', '=', True),
        ], order='name')
        categories = request.env['product.public.category'].sudo().search([], order='sequence')
        return request.render('food_kiosk.landing_page', {
            'products': products,
            'categories': categories,
        })

    @http.route('/kiosk', type='http', auth='public', website=True)
    def kiosk_home(self, **kw):
        """Main kiosk screen — full screen, touch-optimized."""
        products = request.env['product.product'].sudo().search([
            ('type', '=', 'consu'),
            ('sale_ok', '=', True),
        ], order='name')
        categories = request.env['product.public.category'].sudo().search([], order='sequence')
        return request.render('food_kiosk.kiosk_home', {
            'products': products,
            'categories': categories,
        })

    @http.route('/kiosk/create_order', type='json', auth='public')
    def create_order(self, **data):
        """Create a sale order and get Flow payment URL via agent."""
        _logger.info("Food Kiosk: create_order called")

        # Get or create anonymous partner
        partner = request.env['res.partner'].sudo().search([], limit=1)
        if not partner:
            partner = request.env['res.partner'].sudo().create({
                'name': 'Kiosk Customer',
            })

        # Create sale order
        order_ref = request.env['ir.sequence'].sudo().next_by_code('kiosk.order') or 'K-000001'
        order = request.env['sale.order'].sudo().create({
            'partner_id': partner.id,
            'client_order_ref': order_ref,
        })

        # Add product from data if provided
        product_id = data.get('product_id')
        if product_id:
            product = request.env['product.product'].sudo().browse(int(product_id))
            if product:
                order.order_line = [(0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': data.get('qty', 1),
                    'price_unit': data.get('price', product.lst_price),
                })]
            order._compute_amount_total()

        # If no product added, use default kiosk product/amount
        amount = data.get('amount', 9990)

        # Call agent to create Flow payment
        try:
            payment_resp = requests.post(
                f"{AGENT_URL}/create_payment",
                json={
                    "amount": amount,
                    "order_id": order.id,
                    "order_ref": order.client_order_ref,
                },
                timeout=15
            )
            payment_resp.raise_for_status()
            payment_data = payment_resp.json()
        except Exception as e:
            _logger.error(f"Food Kiosk: Agent call failed: {e}")
            return {
                "error": f"Payment service unavailable: {str(e)}",
                "order_id": order.id,
            }

        return {
            "payment_url": payment_data.get("url"),
            "token": payment_data.get("token"),
            "order_id": order.id,
            "order_ref": order.client_order_ref,
        }

    @http.route('/kiosk/payment_webhook', type='http', auth='public', csrf=False, methods=['POST', 'GET'])
    def payment_webhook(self, **kw):
        """Webhook from Flow.cl via agent — confirms payment."""
        _logger.info(f"Food Kiosk: payment_webhook received: {kw}")

        status = kw.get('status')
        commerce_order = kw.get('commerce_order', '')
        order_id = kw.get('order_id')

        order = None
        if commerce_order:
            order = request.env['sale.order'].sudo().search(
                [('client_order_ref', '=', commerce_order)],
                limit=1
            )
        elif order_id:
            order = request.env['sale.order'].sudo().browse(int(order_id))

        if order and status == 'paid':
            if order.state == 'draft':
                order.action_confirm()
                _logger.info(f"Food Kiosk: Order {order.name} confirmed via webhook")
            return "ok"

        _logger.warning(f"Food Kiosk: Webhook skipped - order={order}, status={status}")
        return "ok"

    @http.route('/kiosk/return', type='http', auth='public', website=True)
    def payment_return(self, **kw):
        """Return page after Flow payment."""
        token = kw.get('token', '')
        order_id = kw.get('order_id')
        order = None
        qr_codes = []

        if order_id:
            order = request.env['sale.order'].sudo().browse(int(order_id))

            # Generate QR codes for recyclable items in the order
            try:
                # Call agent /decide endpoint to generate QR tokens
                decide_resp = requests.post(
                    f"{AGENT_URL}/decide",
                    json={
                        "vertical": "KIOSK",
                        "intent": "ACTION",
                        "data": {
                            "order_id": int(order_id),
                            "items": ["combo"],  # Default: assume combo with packaging
                        },
                        "metadata": {},
                    },
                    timeout=10
                )
                if decide_resp.status_code == 200:
                    result = decide_resp.json()
                    if result.get('qr_tokens'):
                        qr_codes = result['qr_tokens']
            except Exception as e:
                _logger.warning(f"Failed to generate QR codes: {e}")

        return request.render('food_kiosk.kiosk_return', {
            'order': order,
            'token': token,
            'status': kw.get('status', 'pending'),
            'qr_codes': qr_codes,
        })

    @http.route('/kiosk/order/<int:order_id>', type='http', auth='public', website=True)
    def kiosk_order_status(self, order_id, **kw):
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order or order.id != order_id:
            return request.render('food_kiosk.kiosk_error', {'message': 'Order not found'})
        return request.render('food_kiosk.kiosk_order_status', {'order': order})
