#!/usr/bin/env python3
"""
status-aggregator.py — FastAPI endpoint para OS Portal
Consulta todos los servicios, mide latencia, devuelve JSON limpio.
También loggea en Supabase para historial.

Deploy: /opt/ecocupon/status-aggregator/
Run: uvicorn status_aggregator:app --port 8002
"""

import httpx
import asyncio
import json
import os
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="EcoCupon Status Aggregator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

SERVICES = {
    "agent":   {"url": "http://127.0.0.1:9001/health", "timeout": 3},
    "odoo":    {"url": "http://127.0.0.1:8070", "timeout": 5},
    "qr":      {"url": "http://127.0.0.1:9004/health", "timeout": 3},
    "bolt":    {"url": "http://127.0.0.1:8501/healthz", "timeout": 5},
    "n8n":     {"url": "http://127.0.0.1:5678/healthz", "timeout": 5},
    "caddy":   {"url": "http://127.0.0.1:2019/metrics", "timeout": 2},
    "postgres":{"url": None, "type": "tcp", "host": "127.0.0.1", "port": 5432, "timeout": 2},
    "redis":   {"url": None, "type": "tcp", "host": "127.0.0.1", "port": 6379, "timeout": 2},
    "llm":     {"url": "http://127.0.0.1:8000/health", "timeout": 5},
}

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rjfcmmzjlguiititkmyh.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

_cached_status = None
_last_check = None


async def check_http(url: str, timeout: int) -> dict:
    """Check HTTP service and measure latency."""
    start = asyncio.get_event_loop().time()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, follow_redirects=False)
            latency = int((asyncio.get_event_loop().time() - start) * 1000)
            return {
                "status": "ok" if resp.status_code < 400 else "degraded",
                "latency": latency,
                "http_code": resp.status_code
            }
    except Exception as e:
        latency = int((asyncio.get_event_loop().time() - start) * 1000)
        return {"status": "down", "latency": latency, "error": str(e)}


async def check_tcp(host: str, port: int, timeout: int) -> dict:
    """Check TCP service availability."""
    start = asyncio.get_event_loop().time()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        latency = int((asyncio.get_event_loop().time() - start) * 1000)
        return {"status": "ok", "latency": latency}
    except Exception as e:
        latency = int((asyncio.get_event_loop().time() - start) * 1000)
        return {"status": "down", "latency": latency, "error": str(e)}


async def log_to_supabase(service: str, status: str, latency: int, details: dict):
    """Persist status log to Supabase."""
    if not SUPABASE_KEY:
        return
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"{SUPABASE_URL}/rest/v1/service_status_logs",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json={
                    "service": service,
                    "status": status,
                    "latency_ms": latency,
                    "details": details
                }
            )
    except Exception:
        pass  # Don't fail status check if logging fails


@app.get("/health")
async def health():
    return {"status": "ok", "service": "status-aggregator"}


@app.get("/status.json")
@app.get("/status")
@app.get("/services")
async def get_status():
    global _cached_status, _last_check

    tasks = []
    for name, cfg in SERVICES.items():
        if cfg.get("type") == "tcp":
            tasks.append(check_tcp(cfg["host"], cfg["port"], cfg["timeout"]))
        elif cfg.get("url"):
            tasks.append(check_http(cfg["url"], cfg["timeout"]))
        else:
            tasks.append({"status": "unknown", "latency": 0})

    results = await asyncio.gather(*tasks)

    services = {}
    overall = "ok"
    for (name, cfg), result in zip(SERVICES.items(), results):
        services[name] = result
        if result["status"] != "ok":
            overall = "degraded" if overall != "down" else "down"
            # Log to Supabase
            await log_to_supabase(name, result["status"], result.get("latency", 0), result)

    _cached_status = {
        "status": overall,
        "services": services,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }
    _last_check = datetime.now(timezone.utc)

    return _cached_status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)
