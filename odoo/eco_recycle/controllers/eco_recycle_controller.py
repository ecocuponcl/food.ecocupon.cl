import requests
from odoo import http
from odoo.http import request
import logging

logger = logging.getLogger(__name__)

AGENT_URL = "http://localhost:9000"


class EcoRecycleController(http.Controller):

    @http.route("/recycle/scan", type="http", auth="public", website=True)
    def recycle_scan(self, t=None, **kwargs):
        """QR scan page — validate recycling."""
        if not t:
            return request.render("eco_recycle.recycle_error", {
                "error": "QR inválido"
            })

        # Check token in Odoo
        qr_token = request.env["eco.qr.token"].sudo().search([("token", "=", t)], limit=1)
        if not qr_token:
            return request.render("eco_recycle.recycle_error", {
                "error": "Token no encontrado"
            })
        if qr_token.used:
            return request.render("eco_recycle.recycle_error", {
                "error": "Este envase ya fue reciclado"
            })

        return request.render("eco_recycle.recycle_validate", {
            "qr_token": t,
            "item": qr_token.item,
            "reward": qr_token.reward,
        })

    @http.route("/recycle/submit", type="json", auth="public", csrf=False)
    def recycle_submit(self, **data):
        """Submit recycling validation."""
        qr_token = data.get("qr_token")
        phone = data.get("phone")
        validation_type = data.get("validation_type", "photo")
        photo_url = data.get("photo_url")
        lat = data.get("lat")
        lng = data.get("lng")

        # Call agent for anti-fraud + wallet credit
        try:
            resp = requests.post(f"{AGENT_URL}/recycle/validate", json={
                "qr_token": qr_token,
                "phone": phone,
                "validation_type": validation_type,
                "photo_url": photo_url,
                "lat": lat,
                "lng": lng,
            }, timeout=10)
            result = resp.json()
        except Exception as e:
            logger.error(f"Agent error: {e}")
            return {"error": str(e)}

        if resp.status_code != 200:
            return {"error": result.get("detail", "Error validando reciclaje")}

        # Log in Odoo
        qr_token_obj = request.env["eco.qr.token"].sudo().search([("token", "=", qr_token)], limit=1)
        if qr_token_obj:
            wallet = request.env["eco.wallet"].sudo().search([("phone", "=", phone)], limit=1)
            if not wallet:
                wallet = request.env["eco.wallet"].sudo().create({"phone": phone})

            event = request.env["eco.recycle.event"].sudo().create({
                "qr_token_id": qr_token_obj.id,
                "wallet_id": wallet.id,
                "validation_type": validation_type,
                "photo_url": photo_url,
                "lat": lat or 0,
                "lng": lng or 0,
                "order_id": qr_token_obj.order_id.id,
                "state": "validated",
            })
            event.action_validate()

        return result

    @http.route("/recycle/wallet", type="http", auth="public", website=True)
    def recycle_wallet(self, phone=None, **kwargs):
        """Wallet check page."""
        if not phone:
            return request.render("eco_recycle.wallet_lookup")

        try:
            resp = requests.get(f"{AGENT_URL}/recycle/wallet/{phone}", timeout=10)
            wallet = resp.json()
        except Exception:
            wallet = {"phone": phone, "balance": 0, "history": []}

        return request.render("eco_recycle.wallet_view", {"wallet": wallet})
