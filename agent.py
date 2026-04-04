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
FLOW_BUTTON_TOKEN = os.getenv("FLOW_BUTTON_TOKEN", "zb21aa68cfd8df13c6030369d9946745810db853")
FLOW_API_URL = os.getenv("FLOW_API_URL", "https://www.flow.cl/api/payment/create")
CONFIRM_URL = os.getenv("CONFIRM_URL", "https://food.ecocupon.cl/kiosk/payment_webhook")
RETURN_URL = os.getenv("RETURN_URL", "https://food.ecocupon.cl/kiosk/return")

if not FLOW_API_KEY or not FLOW_SECRET_KEY:
    logger.warning("FLOW credentials not set — payments will fail")


def sign_flow_request(params: dict) -> str:
    """Sign Flow request parameters with HMAC-SHA256."""
    # Remove signature if present
    params_to_sign = {k: v for k, v in params.items() if k != "signature"}
    sorted_params = sorted(params_to_sign.items())
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
@app.get("/")
def root():
    return {
        "service": "Ecocupon Payment Agent",
        "version": "1.0.0",
        "endpoints": {
            "GET /health": "Health check",
            "POST /create_payment": "Create Flow payment",
            "POST /webhook/flow": "Flow webhook receiver",
            "GET /docs": "Swagger UI",
        },
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "ecocupon-agent"}


@app.post("/create_payment", response_model=PaymentResponse)
def create_payment(req: PaymentRequest):
    """Return Flow payment button URL."""

    if not FLOW_BUTTON_TOKEN:
        raise HTTPException(status_code=500, detail="FLOW_BUTTON_TOKEN not configured")

    payment_url = f"https://www.flow.cl/btn.php?token={FLOW_BUTTON_TOKEN}"

    logger.info(f"Payment URL generated: order={req.order_id}, amount={req.amount}")

    return PaymentResponse(url=payment_url, token=FLOW_BUTTON_TOKEN)


@app.post("/webhook/flow")
def flow_webhook(data: dict):
    """Optional: receive Flow webhook callbacks for logging."""
    logger.info(f"Flow webhook received: {data}")
    return {"ok": True}
