"""
Agent - FastAPI payment gateway for Flow.cl
Connects Odoo kiosk orders to Flow payment API.
"""

import os
import hmac
import hashlib
import logging
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Ecocupon Payment Agent", version="1.0.0")

# ── Config ──────────────────────────────────────────────
FLOW_API_KEY = os.getenv("FLOW_API_KEY")
FLOW_SECRET_KEY = os.getenv("FLOW_SECRET_KEY")
FLOW_API_URL = os.getenv("FLOW_API_URL", "https://www.flow.cl/api/payment/create")
CONFIRM_URL = os.getenv("CONFIRM_URL", "https://food.ecocupon.cl/kiosk/payment_webhook")
RETURN_URL = os.getenv("RETURN_URL", "https://food.ecocupon.cl/kiosk/return")

if not FLOW_API_KEY or not FLOW_SECRET_KEY:
    logger.warning("FLOW credentials not set — payments will fail")


def sign_flow_request(params: dict) -> str:
    """Sign Flow request parameters with HMAC-SHA256."""
    sorted_params = sorted(params.items())
    string_to_sign = "&".join(f"{k}={v}" for k, v in sorted_params)
    signature = hmac.new(
        FLOW_SECRET_KEY.encode(),
        string_to_sign.encode(),
        hashlib.sha256,
    ).hexdigest()
    return signature


# ── Models ──────────────────────────────────────────────
class PaymentRequest(BaseModel):
    amount: int
    order_id: int
    subject: Optional[str] = None
    email: Optional[str] = None


class PaymentResponse(BaseModel):
    url: str
    token: str


# ── Routes ──────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "ecocupon-agent"}


@app.post("/create_payment", response_model=PaymentResponse)
def create_payment(req: PaymentRequest):
    """Create a payment via Flow API and return the checkout URL."""

    if not FLOW_API_KEY or not FLOW_SECRET_KEY:
        raise HTTPException(status_code=500, detail="FLOW credentials not configured")

    subject = req.subject or f"Pedido {req.order_id}"

    payload = {
        "apiKey": FLOW_API_KEY,
        "amount": req.amount,
        "subject": subject,
        "currency": "CLP",
        "returnUrl": RETURN_URL,
        "confirmUrl": CONFIRM_URL,
    }

    if req.email:
        payload["payerEmail"] = req.email

    # Sign request
    payload["signature"] = sign_flow_request(payload)

    logger.info(f"Creating payment: order={req.order_id}, amount={req.amount}")

    try:
        resp = requests.post(FLOW_API_URL, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.error(f"Flow API error: {e}")
        raise HTTPException(status_code=502, detail=f"Flow API error: {e}")

    payment_url = data.get("url")
    token = data.get("token")

    if not payment_url or not token:
        logger.error(f"Unexpected Flow response: {data}")
        raise HTTPException(status_code=502, detail="Invalid response from Flow API")

    logger.info(f"Payment created: token={token}, url={payment_url}")

    return PaymentResponse(url=payment_url, token=token)


@app.post("/webhook/flow")
def flow_webhook(data: dict):
    """Optional: receive Flow webhook callbacks for logging."""
    logger.info(f"Flow webhook received: {data}")
    return {"ok": True}
