"""
Food Ecocupon Payment Agent — VPS
Proxies Flow.cl payment button
"""
import os, hmac, hashlib, logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Food Ecocupon Agent", version="1.0.0")

FLOW_API_KEY = os.getenv("FLOW_API_KEY", "")
FLOW_SECRET_KEY = os.getenv("FLOW_SECRET_KEY", "")
FLOW_API_URL = os.getenv("FLOW_API_URL", "https://www.flow.cl/api/payment/create")
FLOW_BUTTON_URL = os.getenv("FLOW_BUTTON_URL", "")
CONFIRM_URL = os.getenv("CONFIRM_URL", "https://food.ecocupon.cl/kiosk/payment_webhook")
RETURN_URL = os.getenv("RETURN_URL", "https://food.ecocupon.cl/kiosk/return")

def sign_flow_request(params: dict) -> str:
    sorted_params = sorted(params.items())
    string_to_sign = "&".join(f"{k}={v}" for k, v in sorted_params)
    return hmac.new(
        FLOW_SECRET_KEY.encode(), string_to_sign.encode(), hashlib.sha256
    ).hexdigest()

class PaymentRequest(BaseModel):
    amount: int
    order_id: int
    order_ref: str = ""

@app.get("/health")
def health():
    return {"status": "ok", "service": "food-agent", "on": "vps"}

@app.post("/create_payment")
def create_payment(req: PaymentRequest):
    # If we have a pre-configured Flow button URL, use it directly
    if FLOW_BUTTON_URL and FLOW_BUTTON_URL != "":
        logger.info(f"Using Flow button URL: order={req.order_id}, amount={req.amount}")
        return {
            "url": FLOW_BUTTON_URL,
            "token": FLOW_BUTTON_URL.split("token=")[-1] if "token=" in FLOW_BUTTON_URL else "",
            "order_id": req.order_id,
        }

    if not FLOW_API_KEY:
        logger.info(f"Test mode: order={req.order_id}, amount={req.amount}")
        return {
            "url": f"{RETURN_URL}?status=paid&order_id={req.order_id}",
            "token": "test-mode",
            "order_id": req.order_id,
        }

    subject = f"Pedido {req.order_ref or req.order_id}"
    payload = {
        "apiKey": FLOW_API_KEY,
        "amount": req.amount,
        "subject": subject,
        "currency": "CLP",
        "returnUrl": RETURN_URL,
        "confirmUrl": CONFIRM_URL,
    }
    if FLOW_SECRET_KEY:
        payload["signature"] = sign_flow_request(payload)

    try:
        resp = requests.post(FLOW_API_URL, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("url") or not data.get("token"):
            raise HTTPException(502, f"Invalid Flow response: {data}")
        return {"url": data["url"], "token": data["token"], "order_id": req.order_id}
    except requests.RequestException as e:
        logger.error(f"Flow API error: {e}")
        raise HTTPException(502, f"Flow API error: {e}")

@app.post("/webhook/flow")
def flow_webhook(data: dict):
    logger.info(f"Flow webhook: {data}")
    return {"ok": True}
