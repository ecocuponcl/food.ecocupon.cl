"""
Food Ecocupon Payment Agent
FastAPI proxy to Flow.cl payment gateway
Run: uvicorn agent:app --host 0.0.0.0 --port 9000
"""
from fastapi import FastAPI
from pydantic import BaseModel
import requests
import logging

app = FastAPI(title="Food Ecocupon Agent", version="1.0.0")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ═══ CONFIG ═══
FLOW_API = "https://www.flow.cl/api/payment/create"
FLOW_KEY = "TU_API_KEY"  # ← Reemplazar con tu API key de Flow.cl
RETURN_URL = "https://food.ecocupon.cl/kiosk/return"
CONFIRM_URL = "https://food.ecocupon.cl/kiosk/payment_webhook"


class PaymentRequest(BaseModel):
    amount: int
    order_id: int
    order_ref: str = ""


@app.post("/create_payment")
def create_payment(req: PaymentRequest):
    """Create a payment via Flow.cl and return payment URL."""
    logger.info(f"Creating payment: ${req.amount} for order {req.order_ref or req.order_id}")

    try:
        resp = requests.post(FLOW_API, json={
            "apiKey": FLOW_KEY,
            "amount": req.amount,
            "subject": f"Pedido {req.order_ref or req.order_id}",
            "buyer_email": "",
            "url_confirmation": CONFIRM_URL,
            "url_return": RETURN_URL,
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        logger.info(f"Flow.cl response: {data}")
        return {
            "url": data.get("url"),
            "token": data.get("token"),
        }
    except Exception as e:
        logger.error(f"Flow.cl API error: {e}")
        return {"error": str(e)}


@app.get("/health")
def health():
    return {"status": "ok", "service": "food-ecocupon-agent"}


@app.get("/docs")
def docs():
    """Swagger UI is at /docs (FastAPI default)"""
    pass
