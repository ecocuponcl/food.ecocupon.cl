"""
EcoCupon Agent — IA Decision Engine
====================================
Motor de arbitraje de activos: residuos, vehículos, kiosk.
IA decide → n8n ejecuta → Supabase recuerda.

Verticales:
  - RECYCLE: foto envase → cashback
  - VEHICLE: patente + precio → comprar/negociar/descartar
  - KIOSK: compra food → QR envase → cashback
"""

import os
import hmac
import hashlib
import uuid
import time
import json
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

app = FastAPI(title="EcoCupon Agent — IA Decision Engine", version="3.0.0")

# ── Config ──────────────────────────────────────────────
FLOW_API_KEY = os.getenv("FLOW_API_KEY")
FLOW_SECRET_KEY = os.getenv("FLOW_SECRET_KEY")
FLOW_BUTTON_TOKEN = os.getenv("FLOW_BUTTON_TOKEN", "zb21aa68cfd8df13c6030369d9946745810db853")
FLOW_API_URL = os.getenv("FLOW_API_URL", "https://www.flow.cl/api/payment/create")
CONFIRM_URL = os.getenv("CONFIRM_URL", "https://food.ecocupon.cl/kiosk/payment_webhook")
RETURN_URL = os.getenv("RETURN_URL", "https://food.ecocupon.cl/kiosk/return")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# n8n
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")

# OpenRouter / LLM
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3-70b-instruct")

# Anti-fraud limits
MAX_CASHBACK_PER_DAY = 5000
MIN_MINUTES_BETWEEN_PURCHASE_AND_RECYCLE = 15
MAX_RECYCLES_PER_DAY = 10

if not FLOW_API_KEY or not FLOW_SECRET_KEY:
    logger.warning("FLOW credentials not set")
if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("Supabase not configured — using in-memory store")
if not N8N_WEBHOOK_URL:
    logger.warning("n8n not configured — events logged only")
if not OPENROUTER_API_KEY:
    logger.warning("OpenRouter not configured — using rule-based decisions")


# ── Supabase Client ────────────────────────────────────
def supabase_post(table: str, data: dict) -> Optional[dict]:
    """Insert into Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/{table}",
            json=data,
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Supabase POST error: {e}")
        return None


def supabase_get(table: str, params: dict) -> Optional[list]:
    """Query Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/{table}?{query}",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Supabase GET error: {e}")
        return None


def log_event(source: str, event_type: str, payload: dict):
    """Log everything to Supabase events_log."""
    supabase_post("events_log", {
        "source": source,
        "type": event_type,
        "payload": payload,
    })


# ── In-Memory Store (fallback if no Supabase) ──────────
wallets: dict[str, dict] = {}
recycle_events: list[dict] = []
qr_tokens: dict[str, dict] = {}
daily_limits: dict[str, dict] = {}
vehicle_scoring_cache: dict[str, dict] = {}


def _get_daily(phone: str) -> dict:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if phone not in daily_limits or daily_limits[phone]["date"] != today:
        daily_limits[phone] = {"date": today, "amount": 0, "count": 0}
    return daily_limits[phone]


def _check_fraud(phone: str, reward: int, purchase_time: Optional[float] = None) -> dict:
    """Anti-fraud checks. Returns {blocked: bool, reason: str}."""
    daily = _get_daily(phone)

    if daily["count"] >= MAX_RECYCLES_PER_DAY:
        return {"blocked": True, "reason": f"Límite diario: {MAX_RECYCLES_PER_DAY} reciclajes"}
    if daily["amount"] + reward > MAX_CASHBACK_PER_DAY:
        return {"blocked": True, "reason": f"Límite cashback: ${MAX_CASHBACK_PER_DAY}/día"}
    if purchase_time:
        elapsed = time.time() - purchase_time
        min_seconds = MIN_MINUTES_BETWEEN_PURCHASE_AND_RECYCLE * 60
        if elapsed < min_seconds:
            return {"blocked": True, "reason": f"Espera {MIN_MINUTES_BETWEEN_PURCHASE_AND_RECYCLE} min"}

    return {"blocked": False, "reason": ""}


# ── System Prompts (3 verticals) ───────────────────────
SYSTEM_PROMPTS = {
    "RECYCLE": """Eres un tasador de residuos para EcoCupon Chile.
Analiza el item y determina:
1. Tipo de material (PET, aluminio, vidrio, cartón, orgánico)
2. Estado (limpio, dañado, contaminado)
3. Valor de cashback en CLP basado en:
   - PET 500ml: $50, 1L: $80, 1.5L: $100
   - Aluminio (lata): $30
   - Vidrio 330ml: $40, 750ml: $60
   - Cartón limpio: $20
   - Orgánico: $0 (no aplica)
4. Riesgo de fraude (0-100): foto duplicada, GPS sospechoso, frecuencia anormal

Responde SOLO con JSON válido.""",

    "VEHICLE": """Eres un tasador de vehículos usados para EcoCupon Chile.
Analiza el vehículo y determina:
1. Valor de mercado estimado en CLP (usando datos de mercado chileno)
2. Comparación con precio publicado (% sobreprecio o bajo precio)
3. Recomendación: COMPRAR (precio justo), NEGOCIAR (sobreprecio <20%), DESCARTAR (sobreprecio >20% o alertas)
4. Riesgo de fraude (0-100): precio sospechoso, datos inconsistentes
5. Valor de reciclaje/chatarrería si se descarta (aprox 8-12% del valor original)

Referencias mercado Chile 2026:
- Auto básico 2015-2018: $3.000.000 - $5.000.000
- Auto medio 2018-2022: $5.000.000 - $9.000.000
- Auto premium 2020+: $10.000.000+
- Camioneta 2018-2022: $8.000.000 - $15.000.000

Responde SOLO con JSON válido.""",

    "KIOSK": """Eres el motor de decisión para un kiosco táctil de comida.
Analiza la compra y genera:
1. QR único para cada envase del pedido
2. Cashback por envase según tipo
3. Recomendación de reciclaje al cliente
4. Total cashback potencial si recicla todo

Tipos de envase en pedidos food:
- Sixpack cerveza: $100 cashback
- Botella bebida 1.5L: $80
- Lata individual: $30
- Caja cartón: $20
- Bolsa plástico: $0

Responde SOLO con JSON válido."""
}


# ── LLM Decision Engine ────────────────────────────────
def call_llm(system_prompt: str, user_input: str) -> Optional[dict]:
    """Call LLM for decision. Returns parsed JSON or None."""
    if not OPENROUTER_API_KEY:
        return None

    try:
        resp = requests.post(
            OPENROUTER_URL,
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                "temperature": 0.1,
                "max_tokens": 1000,
            },
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://food.ecocupon.cl",
                "X-Title": "EcoCupon Agent",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()

        # Extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        return json.loads(content)
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return None


# ── Universal Decision Schema ──────────────────────────
class DecisionRequest(BaseModel):
    vertical: Literal["RECYCLE", "VEHICLE", "KIOSK"]
    intent: Literal["EVALUATE", "ACTION", "SUPPORT"] = "EVALUATE"
    data: dict = Field(..., description="Input data for the vertical")
    metadata: Optional[dict] = Field(default=None, description="user_phone, lat, lng, etc.")


class ScoringResult(BaseModel):
    confidence: float = 0.0
    value_clp: int = 0
    reasoning: str = ""


class DecisionResponse(BaseModel):
    vertical: str
    intent: str
    scoring: ScoringResult
    decision: str = ""  # approve/reject/review for recycle, comprar/negociar/descartar for vehicle
    options: list[dict] = []
    metadata: dict = {}
    next_step: str = ""
    event_id: str = ""


@app.post("/decide", response_model=DecisionResponse)
def decide(req: DecisionRequest):
    """
    Universal decision endpoint.
    Routes to the correct vertical logic (LLM + rules).
    """
    event_id = str(uuid.uuid4())
    system_prompt = SYSTEM_PROMPTS.get(req.vertical, SYSTEM_PROMPTS["RECYCLE"])

    # Build user input for LLM
    user_input = json.dumps(req.data, ensure_ascii=False)

    # Try LLM first
    llm_result = call_llm(system_prompt, user_input)

    # Fallback to rule-based
    if req.vertical == "RECYCLE":
        result = _decide_recycle(req.data, llm_result)
    elif req.vertical == "VEHICLE":
        result = _decide_vehicle(req.data, llm_result)
    elif req.vertical == "KIOSK":
        result = _decide_kiosk(req.data, llm_result)
    else:
        raise HTTPException(400, f"Unknown vertical: {req.vertical}")

    # Add metadata
    result["metadata"] = req.metadata or {}
    result["metadata"]["event_id"] = event_id
    result["event_id"] = event_id
    result["vertical"] = req.vertical
    result["intent"] = req.intent

    # Log to Supabase
    log_event("agent", f"decide.{req.vertical}", {
        "event_id": event_id,
        "vertical": req.vertical,
        "input": req.data,
        "output": result,
        "llm_used": llm_result is not None,
    })

    # Trigger n8n webhook
    if N8N_WEBHOOK_URL:
        try:
            requests.post(N8N_WEBHOOK_URL, json=result, timeout=10)
            result["next_step"] = "n8n_triggered"
        except Exception as e:
            logger.error(f"n8n webhook error: {e}")
            result["next_step"] = "n8n_failed"
    else:
        result["next_step"] = "n8n_not_configured"

    return DecisionResponse(**result)


# ── Vertical: RECYCLE ─────────────────────────────────
def _decide_recycle(data: dict, llm_result: Optional[dict]) -> dict:
    """Recycle decision: item → value + fraud check."""
    item = data.get("item", "").lower()
    photo_url = data.get("photo_url", "")
    phone = data.get("phone", "")

    # Rule-based pricing
    pricing = {
        "pet": 50, "pet_500": 50, "pet_1l": 80, "pet_1.5l": 100,
        "aluminio": 30, "lata": 30,
        "vidrio": 40, "vidrio_330": 40, "vidrio_750": 60,
        "carton": 20,
        "organico": 0,
    }

    value = 0
    for key, price in pricing.items():
        if key in item:
            value = price
            break

    # LLM override if available
    if llm_result:
        value = llm_result.get("value_clp", value)
        reasoning = llm_result.get("reasoning", f"IA: {item}")
        fraud_score = llm_result.get("fraud_score", 0)
    else:
        reasoning = f"Rule-based: {item} = ${value}"
        fraud_score = 0

    # Fraud check
    fraud_check = _check_fraud(phone, value) if phone else {"blocked": False, "reason": ""}

    if fraud_check["blocked"]:
        return {
            "scoring": {"confidence": 0.95, "value_clp": 0, "reasoning": fraud_check["reason"]},
            "decision": "reject",
            "options": [],
        }

    decision = "approve" if fraud_score < 70 else ("review" if fraud_score < 90 else "reject")

    return {
        "scoring": {
            "confidence": 0.9 if llm_result else 0.7,
            "value_clp": value,
            "reasoning": reasoning,
        },
        "decision": decision,
        "options": [
            {"action": "cashback", "amount": value, "label": f"+${value} CLP a wallet"},
            {"action": "donate", "amount": value, "label": f"Donar ${value} a causa verde"},
        ],
    }


# ── Vertical: VEHICLE ─────────────────────────────────
def _decide_vehicle(data: dict, llm_result: Optional[dict]) -> dict:
    """Vehicle decision: patent + price → buy/negotiate/discard."""
    price = data.get("precio", 0)
    marca = data.get("marca", "")
    modelo = data.get("modelo", "")
    ano = data.get("ano", 2020)

    # Rule-based market estimate
    base_values = {
        "chevrolet": 4000000, "toyota": 7000000, "hyundai": 5500000,
        "kia": 5000000, "nissan": 4500000, "suzuki": 4000000,
        "mazda": 6000000, "volkswagen": 6500000, "bmw": 15000000,
    }

    base = 0
    for brand, val in base_values.items():
        if brand in marca.lower():
            base = val
            break

    if not base:
        base = 5000000  # default

    # Age adjustment
    age = 2026 - ano
    estimated = int(base * (0.92 ** age))

    # LLM override
    if llm_result:
        estimated = llm_result.get("value_clp", estimated)
        reasoning = llm_result.get("reasoning", f"IA valuation")
    else:
        reasoning = f"Rule-based: {marca} {modelo} {ano} ≈ ${estimated:,}"

    # Decision
    if price == 0:
        decision = "evaluar"
        options = [{"action": "info", "label": "Ingresa precio para comparar"}]
    else:
        diff_pct = ((price - estimated) / estimated) * 100

        if diff_pct > 20:
            decision = "descartar"
            recycle_value = int(estimated * 0.10)
            options = [
                {"action": "reject", "label": f"Sobreprecio {diff_pct:.0f}% — no comprar"},
                {"action": "recycle_alt", "label": f"Valor chatarrería: ~${recycle_value:,}"},
            ]
        elif diff_pct > 5:
            decision = "negociar"
            suggested = int(estimated * 0.97)
            options = [
                {"action": "negotiate", "label": f"Ofrecer: ${suggested:,}"},
                {"action": "wait", "label": "Esperar baja de precio"},
            ]
        else:
            decision = "comprar"
            options = [
                {"action": "buy", "label": f"Precio justo — comprar"},
                {"action": "negotiate", "label": f"Intentar ${int(estimated * 0.95):,}"},
            ]

    return {
        "scoring": {
            "confidence": 0.85 if llm_result else 0.65,
            "value_clp": estimated,
            "reasoning": reasoning,
        },
        "decision": decision,
        "options": options,
    }


# ── Vertical: KIOSK ───────────────────────────────────
def _decide_kiosk(data: dict, llm_result: Optional[dict]) -> dict:
    """Kiosk decision: order → QR tokens + cashback potential."""
    order_id = data.get("order_id", 0)
    items = data.get("items", [])

    packaging_map = {
        "sixpack": {"type": "sixpack", "reward": 100, "label": "Sixpack cerveza"},
        "cerveza": {"type": "sixpack", "reward": 100, "label": "Sixpack cerveza"},
        "bebida": {"type": "botella_1.5l", "reward": 80, "label": "Botella bebida 1.5L"},
        "botella": {"type": "botella_1.5l", "reward": 80, "label": "Botella bebida 1.5L"},
        "lata": {"type": "lata", "reward": 30, "label": "Lata individual"},
        "hamburguesa": {"type": "caja_carton", "reward": 20, "label": "Caja cartón"},
        "combo": {"type": "mix", "reward": 150, "label": "Combo completo"},
    }

    qr_items = []
    total_cashback = 0

    for item_name in items:
        name_lower = item_name.lower()
        matched = None
        for key, pkg in packaging_map.items():
            if key in name_lower:
                matched = pkg
                break

        if matched:
            qr_items.append(matched)
            total_cashback += matched["reward"]

    # LLM override
    if llm_result:
        total_cashback = llm_result.get("total_cashback", total_cashback)

    # Generate QR tokens
    generated_qrs = []
    for pkg in qr_items:
        token = uuid.uuid4().hex[:16]
        qr_tokens[token] = {
            "order_id": order_id,
            "item": pkg["type"],
            "reward": pkg["reward"],
            "used": False,
            "created_at": time.time(),
        }
        generated_qrs.append({
            "token": token,
            "url": f"https://food.ecocupon.cl/recycle/scan?t={token}",
            "item": pkg["label"],
            "reward": pkg["reward"],
        })

    return {
        "scoring": {
            "confidence": 0.95,
            "value_clp": total_cashback,
            "reasoning": f"{len(qr_items)} envases reciclables detectados",
        },
        "decision": "qr_generated",
        "options": [
            {"action": "print_qr", "label": f"Imprimir {len(generated_qrs)} QR en ticket"},
            {"action": "show_cashback", "label": f"Cashback potencial: ${total_cashback} CLP"},
        ],
        "qr_tokens": generated_qrs,
        "total_cashback": total_cashback,
    }


# ── Legacy Routes (still work) ─────────────────────────
@app.get("/")
def root():
    return {
        "service": "EcoCupon Agent — IA Decision Engine",
        "version": "3.0.0",
        "verticals": ["RECYCLE", "VEHICLE", "KIOSK"],
        "modules": ["decide", "payments", "recycle", "wallet", "vehicle"],
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "ecocupon-agent",
        "wallets": len(wallets),
        "recycles": len(recycle_events),
        "qr_tokens": len(qr_tokens),
        "llm_configured": bool(OPENROUTER_API_KEY),
        "supabase_configured": bool(SUPABASE_URL and SUPABASE_KEY),
        "n8n_configured": bool(N8N_WEBHOOK_URL),
    }


@app.post("/create_payment")
def create_payment(req: dict):
    """Flow payment URL."""
    if not FLOW_BUTTON_TOKEN:
        raise HTTPException(500, "FLOW_BUTTON_TOKEN not configured")
    return {"url": f"https://www.flow.cl/btn.php?token={FLOW_BUTTON_TOKEN}", "token": FLOW_BUTTON_TOKEN}


@app.post("/webhook/flow")
def flow_webhook(data: dict):
    logger.info(f"Flow webhook: {data}")
    log_event("flow", "webhook", data)
    return {"ok": True}


# ── Recycle Routes ─────────────────────────────────────
@app.post("/recycle/generate_qr")
def generate_qr(req: dict):
    """Generate QR for packaging."""
    order_id = req.get("order_id", 0)
    item = req.get("item", "unknown")
    reward = req.get("reward", 0)

    token = uuid.uuid4().hex[:16]
    qr_tokens[token] = {
        "order_id": order_id, "item": item, "reward": reward,
        "used": False, "created_at": time.time(),
    }
    return {
        "qr_token": token,
        "qr_url": f"https://food.ecocupon.cl/recycle/scan?t={token}",
        "item": item, "reward": reward,
    }


@app.post("/recycle/validate")
def validate_recycle(req: dict):
    """Validate recycling → cashback."""
    qr_token = req.get("qr_token", "")
    phone = req.get("phone", "")

    if qr_token not in qr_tokens:
        raise HTTPException(400, "QR inválido")
    if qr_tokens[qr_token]["used"]:
        raise HTTPException(400, "QR ya utilizado")

    reward = qr_tokens[qr_token]["reward"]
    fraud = _check_fraud(phone, reward)
    if fraud["blocked"]:
        raise HTTPException(400, fraud["reason"])

    if phone not in wallets:
        wallets[phone] = {"balance": 0, "history": []}
    wallets[phone]["balance"] += reward
    wallets[phone]["history"].append({
        "type": "cashback", "amount": reward,
        "item": qr_tokens[qr_token]["item"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    daily = _get_daily(phone)
    daily["amount"] += reward
    daily["count"] += 1

    qr_tokens[qr_token]["used"] = True
    qr_tokens[qr_token]["recycled_at"] = time.time()
    qr_tokens[qr_token]["phone"] = phone

    event = {
        "qr_token": qr_token, "phone": phone,
        "item": qr_tokens[qr_token]["item"], "reward": reward,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    recycle_events.append(event)
    log_event("recycle", "validate", event)

    return {
        "status": "credited", "reward": reward,
        "wallet_balance": wallets[phone]["balance"],
        "message": f"+${reward} CLP por reciclar",
    }


@app.get("/recycle/wallet/{phone}")
def get_wallet(phone: str):
    if phone not in wallets:
        wallets[phone] = {"balance": 0, "history": []}
    return {"phone": phone, "balance": wallets[phone]["balance"],
            "history": wallets[phone]["history"][-20:]}


@app.post("/recycle/wallet/{phone}/withdraw")
def withdraw_wallet(phone: str, amount: Optional[int] = None):
    if phone not in wallets:
        raise HTTPException(404, "Wallet no existe")
    balance = wallets[phone]["balance"]
    if amount is None:
        amount = balance
    if amount > balance:
        raise HTTPException(400, f"Saldo insuficiente: ${balance}")
    wallets[phone]["balance"] -= amount
    wallets[phone]["history"].append({
        "type": "withdraw", "amount": -amount,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return {"status": "withdrawn", "amount": amount, "remaining": wallets[phone]["balance"]}


@app.get("/recycle/stats")
def recycle_stats():
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


# ── Vehicle Routes ─────────────────────────────────────
@app.post("/vehicle/evaluate")
def evaluate_vehicle(req: dict):
    """Evaluate a vehicle for purchase decision."""
    result = _decide_vehicle(req, None)
    result["metadata"] = req.get("metadata", {})
    result["vertical"] = "VEHICLE"
    log_event("vehicle", "evaluate", {"input": req, "output": result})
    return result


# ── Fraud Check (standalone) ───────────────────────────
@app.post("/fraud-check")
def fraud_check(req: dict):
    """Standalone fraud check endpoint."""
    phone = req.get("phone", "")
    reward = req.get("reward", 0)
    purchase_time = req.get("purchase_time")
    lat = req.get("lat")
    lng = req.get("lng")
    photo_url = req.get("photo_url", "")

    fraud = _check_fraud(phone, reward, purchase_time)

    # GPS clustering check
    gps_risk = 0
    if lat and lng:
        recent = [e for e in recycle_events if e.get("lat") and e.get("lng")]
        same_area = sum(1 for e in recent
                       if abs(e["lat"] - lat) < 0.001 and abs(e["lng"] - lng) < 0.001)
        if same_area > 5:
            gps_risk = 40

    # Photo duplicate check
    photo_risk = 0
    if photo_url:
        duplicates = sum(1 for e in recycle_events if e.get("photo_url") == photo_url)
        if duplicates > 0:
            photo_risk = 80

    total_risk = gps_risk + photo_risk
    if fraud["blocked"]:
        total_risk = 100

    decision = "approve" if total_risk < 40 else ("review" if total_risk < 70 else "reject")

    return {
        "decision": decision,
        "score": total_risk,
        "blocked": fraud["blocked"],
        "reason": fraud["reason"] or f"GPS risk: {gps_risk}, Photo risk: {photo_risk}",
    }
