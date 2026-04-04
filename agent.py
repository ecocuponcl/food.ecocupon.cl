"""
EcoCupon Agent — FastAPI gateway
- Flow.cl payments
- Recycle validation + cashback
- Wallet management
"""

import os
import hmac
import hashlib
import uuid
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Literal

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="EcoCupon Agent", version="2.0.0")

# ── Config ──────────────────────────────────────────────
FLOW_API_KEY = os.getenv("FLOW_API_KEY")
FLOW_SECRET_KEY = os.getenv("FLOW_SECRET_KEY")
FLOW_BUTTON_TOKEN = os.getenv("FLOW_BUTTON_TOKEN", "zb21aa68cfd8df13c6030369d9946745810db853")
FLOW_API_URL = os.getenv("FLOW_API_URL", "https://www.flow.cl/api/payment/create")
CONFIRM_URL = os.getenv("CONFIRM_URL", "https://food.ecocupon.cl/kiosk/payment_webhook")
RETURN_URL = os.getenv("RETURN_URL", "https://food.ecocupon.cl/kiosk/return")

# Anti-fraud limits
MAX_CASHBACK_PER_DAY = 5000  # CLP
MIN_MINUTES_BETWEEN_PURCHASE_AND_RECYCLE = 15
MAX_RECYCLES_PER_DAY = 10

if not FLOW_API_KEY or not FLOW_SECRET_KEY:
    logger.warning("FLOW credentials not set — payments will fail")


# ── In-Memory Store (MVP — replace with Supabase later) ─
wallets: dict[str, dict] = {}          # phone → {balance, history}
recycle_events: list[dict] = []        # list of validated recycles
qr_tokens: dict[str, dict] = {}        # token → {order_id, item, used}
daily_limits: dict[str, dict] = {}     # phone → {date, amount, count}


def _get_daily(phone: str) -> dict:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if phone not in daily_limits or daily_limits[phone]["date"] != today:
        daily_limits[phone] = {"date": today, "amount": 0, "count": 0}
    return daily_limits[phone]


def _check_fraud(phone: str, reward: int, purchase_time: Optional[float] = None) -> None:
    """Anti-fraud checks."""
    daily = _get_daily(phone)

    if daily["count"] >= MAX_RECYCLES_PER_DAY:
        raise HTTPException(400, f"Límite diario alcanzado ({MAX_RECYCLES_PER_DAY} reciclajes)")

    if daily["amount"] + reward > MAX_CASHBACK_PER_DAY:
        raise HTTPException(400, f"Límite diario de cashback: ${MAX_CASHBACK_PER_DAY}")

    if purchase_time:
        elapsed = time.time() - purchase_time
        min_seconds = MIN_MINUTES_BETWEEN_PURCHASE_AND_RECYCLE * 60
        if elapsed < min_seconds:
            raise HTTPException(
                400,
                f"Espera {MIN_MINUTES_BETWEEN_PURCHASE_AND_RECYCLE} min después de la compra",
            )


# ── Models ──────────────────────────────────────────────
class PaymentRequest(BaseModel):
    amount: int
    order_id: int
    subject: Optional[str] = None
    email: Optional[str] = None


class PaymentResponse(BaseModel):
    url: str
    token: str


class QRGenerateRequest(BaseModel):
    order_id: int
    item: str = Field(..., description="Tipo de envase: sixpack, botella, lata, etc.")
    reward: int = Field(..., ge=0, description="Cashback en CLP")


class QRGenerateResponse(BaseModel):
    qr_token: str
    qr_url: str
    item: str
    reward: int


class RecycleValidateRequest(BaseModel):
    qr_token: str
    phone: str
    validation_type: Literal["photo", "gps", "truck"] = "photo"
    photo_url: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    purchase_time: Optional[float] = None


class RecycleValidateResponse(BaseModel):
    status: str
    reward: int
    wallet_balance: int
    message: str


class WalletResponse(BaseModel):
    phone: str
    balance: int
    history: list[dict]


# ── Payment Routes ──────────────────────────────────────
@app.get("/")
def root():
    return {
        "service": "EcoCupon Agent",
        "version": "2.0.0",
        "modules": ["payments", "recycle", "wallet"],
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "ecocupon-agent",
        "wallets": len(wallets),
        "recycles": len(recycle_events),
    }


@app.post("/create_payment", response_model=PaymentResponse)
def create_payment(req: PaymentRequest):
    """Return Flow payment button URL."""
    if not FLOW_BUTTON_TOKEN:
        raise HTTPException(status_code=500, detail="FLOW_BUTTON_TOKEN not configured")

    payment_url = f"https://www.flow.cl/btn.php?token={FLOW_BUTTON_TOKEN}"
    logger.info(f"Payment URL: order={req.order_id}, amount={req.amount}")
    return PaymentResponse(url=payment_url, token=FLOW_BUTTON_TOKEN)


@app.post("/webhook/flow")
def flow_webhook(data: dict):
    """Receive Flow webhook callbacks."""
    logger.info(f"Flow webhook: {data}")
    return {"ok": True}


# ── Recycle Routes ──────────────────────────────────────
@app.post("/recycle/generate_qr", response_model=QRGenerateResponse)
def generate_qr(req: QRGenerateRequest):
    """Generate unique QR token for packaging (post-purchase)."""
    token = uuid.uuid4().hex[:16]
    qr_tokens[token] = {
        "order_id": req.order_id,
        "item": req.item,
        "reward": req.reward,
        "used": False,
        "created_at": time.time(),
    }
    qr_url = f"https://food.ecocupon.cl/recycle/scan?t={token}"
    logger.info(f"QR generated: token={token}, item={req.item}, reward={req.reward}")
    return QRGenerateResponse(qr_token=token, qr_url=qr_url, item=req.item, reward=req.reward)


@app.post("/recycle/validate", response_model=RecycleValidateResponse)
def validate_recycle(req: RecycleValidateRequest):
    """Validate recycling and credit cashback to wallet."""
    # Check QR token
    if req.qr_token not in qr_tokens:
        raise HTTPException(400, "QR inválido")

    token_data = qr_tokens[req.qr_token]
    if token_data["used"]:
        raise HTTPException(400, "QR ya utilizado")

    reward = token_data["reward"]

    # Anti-fraud
    _check_fraud(req.phone, reward, req.purchase_time)

    # Credit wallet
    if req.phone not in wallets:
        wallets[req.phone] = {"balance": 0, "history": []}

    wallets[req.phone]["balance"] += reward
    wallets[req.phone]["history"].append({
        "type": "cashback",
        "amount": reward,
        "item": token_data["item"],
        "qr_token": req.qr_token,
        "validation": req.validation_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Update daily limit
    daily = _get_daily(req.phone)
    daily["amount"] += reward
    daily["count"] += 1

    # Mark QR as used
    token_data["used"] = True
    token_data["recycled_at"] = time.time()
    token_data["phone"] = req.phone

    # Log event
    event = {
        "qr_token": req.qr_token,
        "phone": req.phone,
        "item": token_data["item"],
        "reward": reward,
        "validation_type": req.validation_type,
        "photo_url": req.photo_url,
        "lat": req.lat,
        "lng": req.lng,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    recycle_events.append(event)

    logger.info(f"Recycle validated: phone={req.phone}, item={token_data['item']}, reward=${reward}")

    return RecycleValidateResponse(
        status="credited",
        reward=reward,
        wallet_balance=wallets[req.phone]["balance"],
        message=f"+${reward} CLP por reciclar {token_data['item']}",
    )


@app.get("/recycle/wallet/{phone}", response_model=WalletResponse)
def get_wallet(phone: str):
    """Check wallet balance."""
    if phone not in wallets:
        wallets[phone] = {"balance": 0, "history": []}

    return WalletResponse(
        phone=phone,
        balance=wallets[phone]["balance"],
        history=wallets[phone]["history"][-20:],  # last 20
    )


@app.post("/recycle/wallet/{phone}/withdraw")
def withdraw_wallet(phone: str, amount: Optional[int] = None):
    """Withdraw wallet balance (for next purchase discount)."""
    if phone not in wallets:
        raise HTTPException(404, "Wallet no existe")

    balance = wallets[phone]["balance"]
    if amount is None:
        amount = balance

    if amount > balance:
        raise HTTPException(400, f"Saldo insuficiente: ${balance}")

    wallets[phone]["balance"] -= amount
    wallets[phone]["history"].append({
        "type": "withdraw",
        "amount": -amount,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    logger.info(f"Withdraw: phone={phone}, amount=${amount}")
    return {"status": "withdrawn", "amount": amount, "remaining": wallets[phone]["balance"]}


@app.get("/recycle/stats")
def recycle_stats():
    """Platform statistics."""
    total_cashback = sum(e["reward"] for e in recycle_events)
    items = {}
    for e in recycle_events:
        items[e["item"]] = items.get(e["item"], 0) + 1

    return {
        "total_recycles": len(recycle_events),
        "total_cashback_clp": total_cashback,
        "active_wallets": len([w for w in wallets.values() if w["balance"] > 0]),
        "items_recycled": items,
    }
