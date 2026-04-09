#!/usr/bin/env python3
"""
SmarterBOT SKU Engine
══════════════════════
Converts validated LLM output into sellable SKU packages.

Deploy: /opt/smarterbot/sku-engine.py
Used by: agent-local.py after rule_engine.evaluate() passes
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent
SKU_DIR = BASE_DIR / "skus"
SKU_DIR.mkdir(exist_ok=True)

# Price catalog (UF)
PRICE_UF = {
    "CLAWBOT": {"setup": 25, "monthly": 5},
    "Hosting": {"setup": 5, "monthly": 2},
    "Kiosk": {"setup": 15, "monthly": 3},
    "Odoo": {"setup": 30, "monthly": 8},
    "n8n": {"setup": 10, "monthly": 3},
    "Dashboard": {"setup": 8, "monthly": 2},
    "General": {"setup": 10, "monthly": 2}
}

UF_CLP = 38000  # 1 UF ≈ 38,000 CLP


def calculate_setup_price(output: dict) -> dict:
    """Calculate setup + monthly price based on product."""
    product = output.get("product", "General").upper()

    # Find matching product
    price = PRICE_UF.get("General")
    for key in PRICE_UF:
        if key in product:
            price = PRICE_UF[key]
            break

    # Adjust based on complexity
    complexity = output.get("complexity", 1.0)
    setup_uf = price["setup"] * complexity
    monthly_uf = price["monthly"] * complexity

    return {
        "setup_uf": round(setup_uf, 1),
        "setup_clp": round(setup_uf * UF_CLP),
        "monthly_uf": round(monthly_uf, 1),
        "monthly_clp": round(monthly_uf * UF_CLP),
        "currency": "CLP",
        "uf_value": UF_CLP
    }


def estimate_hours(output: dict) -> int:
    """Estimate deployment hours."""
    complexity = output.get("complexity", 1.0)
    deliverables = output.get("deliverables", []) or output.get("includes", [])

    base_hours = 8  # Minimum
    hours_per_deliverable = 4

    return max(base_hours, int(len(deliverables) * hours_per_deliverable * complexity))


def package_sku(output: dict, score: dict) -> dict:
    """
    Convert validated output into sellable SKU.
    Returns None if score < 0.70 (not sellable).
    """
    if score.get("final_score", 0) < 0.70:
        return None  # Not sellable

    pricing = calculate_setup_price(output)
    hours = estimate_hours(output)
    sku_id = f"SKU-{int(time.time())}"

    sku = {
        "sku_id": sku_id,
        "name": output.get("title", output.get("name", "Solución SmarterBOT")),
        "description": output.get("description", ""),
        "includes": output.get("deliverables", output.get("includes", [])),
        "pricing": pricing,
        "estimated_hours": hours,
        "time_to_deploy": f"{hours} horas",
        "metrics": output.get("metrics", {}),
        "rule_score": score.get("final_score", 0),
        "delegation_score": score.get("delegation_score", 0),
        "execution_ready": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "ready"
    }

    # Save to disk
    sku_file = SKU_DIR / f"{sku_id}.json"
    with open(sku_file, "w") as f:
        json.dump(sku, f, indent=2, default=str)

    return sku


def get_sku(sku_id: str) -> dict:
    """Load a SKU by ID."""
    sku_file = SKU_DIR / f"{sku_id}.json"
    if sku_file.exists():
        with open(sku_file) as f:
            return json.load(f)
    return None


def list_skus(limit: int = 20) -> list:
    """List recent SKUs."""
    files = sorted(SKU_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    skus = []
    for f in files[:limit]:
        with open(f) as fh:
            skus.append(json.load(fh))
    return skus


if __name__ == "__main__":
    # Test
    output = {
        "title": "Sistema de Cotizaciones Automatizadas",
        "description": "Automatización completa del flujo de cotizaciones con n8n + Odoo",
        "product": "CLAWBOT",
        "deliverables": ["Workflow n8n", "Dashboard ClickUp", "Integración Odoo", "Telegram alerts"],
        "metrics": {"time_reduction": 0.6, "error_reduction": 0.8},
        "complexity": 1.5
    }

    score = {"final_score": 0.87, "delegation_score": 0.80}

    sku = package_sku(output, score)
    if sku:
        print(f"✅ SKU Created: {sku['sku_id']}")
        print(f"  Name: {sku['name']}")
        print(f"  Setup: {sku['pricing']['setup_uf']} UF (${sku['pricing']['setup_clp']:,} CLP)")
        print(f"  Monthly: {sku['pricing']['monthly_uf']} UF (${sku['pricing']['monthly_clp']:,} CLP)")
        print(f"  Hours: {sku['estimated_hours']}")
        print(f"  Score: {sku['rule_score']}")
    else:
        print("❌ SKU not created (score too low)")
