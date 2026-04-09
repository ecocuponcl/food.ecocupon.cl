#!/usr/bin/env python3
"""
SmarterBOT Rule Engine — BRF (Business Rules Framework)
═══════════════════════════════════════════════════════════
Evaluates LLM output against 53 business rules.
Supports: pre-check, post-check, retry with constraints, delegation scoring.

Deploy: /opt/smarterbot/rule-engine.py
Used by: agent-local.py (BOLT API :8002)
"""

import os
import json
import time
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════
BASE_DIR = Path(__file__).parent
RULES_DIR = BASE_DIR / "rules"
SCORES_DIR = BASE_DIR / "rule-scores"
SCORES_DIR.mkdir(exist_ok=True)

CATEGORY_WEIGHTS = {
    "revenue": 0.30,
    "operations": 0.25,
    "technical": 0.20,
    "ux": 0.15,
    "risk": 0.10
}

THRESHOLDS = {
    "approve": 0.85,
    "warn": 0.70,
    "retry": 0.50,
    "reject": 0.00
}


# ═══════════════════════════════════════════════════════════
# RULE LOADER
# ═══════════════════════════════════════════════════════════
class RuleLoader:
    """Loads and caches all rules from JSON files."""

    def __init__(self, rules_dir: Path = RULES_DIR):
        self.rules_dir = rules_dir
        self._rules: List[Dict] = []
        self._loaded_at = None

    def load(self) -> List[Dict]:
        """Load all rules from JSON files."""
        if self._rules and self._loaded_at:
            # Check if files changed
            mtime = max(f.stat().st_mtime for f in self.rules_dir.glob("*.json") if f.name != "registry.json")
            if mtime <= self._loaded_at:
                return self._rules

        self._rules = []
        for f in sorted(self.rules_dir.glob("*.json")):
            if f.name in ("registry.json", "schema.json"):
                continue
            try:
                with open(f) as fh:
                    rules = json.load(fh)
                    self._rules.extend(rules)
            except Exception as e:
                print(f"⚠️ Failed to load {f}: {e}")

        self._rules.sort(key=lambda r: r.get("severity", "low"))
        self._loaded_at = time.time()
        print(f"📋 Loaded {len(self._rules)} rules")
        return self._rules

    def get_enabled(self) -> List[Dict]:
        """Get only enabled rules."""
        return [r for r in self.load() if r.get("enabled", True)]

    def get_by_category(self, category: str) -> List[Dict]:
        """Get rules by category."""
        return [r for r in self.load() if r.get("category") == category]

    def get_by_phase(self, phase: str) -> List[Dict]:
        """Get rules by phase (pre/post)."""
        return [r for r in self.get_enabled() if r.get("phase", "post") == phase]

    def get_by_id(self, rule_id: str) -> Optional[Dict]:
        """Get rule by ID."""
        for r in self.load():
            if r.get("id") == rule_id:
                return r
        return None


# ═══════════════════════════════════════════════════════════
# RULE EVALUATOR
# ═══════════════════════════════════════════════════════════
class RuleResult:
    """Result of evaluating a single rule."""
    def __init__(self, rule: Dict, passed: bool, detail: str = ""):
        self.rule = rule
        self.passed = passed
        self.detail = detail
        self.timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def id(self): return self.rule.get("id", "?")
    @property
    def category(self): return self.rule.get("category", "?")
    @property
    def severity(self): return self.rule.get("severity", "low")
    @property
    def weight(self): return self.rule.get("weight", 0.05)
    @property
    def action(self): return self.rule.get("action", "warn")
    @property
    def name(self): return self.rule.get("name", "?")


class RuleEvaluator:
    """Evaluates intent + output against business rules."""

    def __init__(self, loader: RuleLoader = None):
        self.loader = loader or RuleLoader()

    def evaluate(self, intent: Dict, output: Dict) -> List[RuleResult]:
        """Evaluate all enabled rules against intent + output."""
        results = []
        context = {"intent": intent, "output": output}

        for rule in self.loader.get_enabled():
            result = self._evaluate_rule(rule, context)
            results.append(result)

        return results

    def _evaluate_rule(self, rule: Dict, context: Dict) -> RuleResult:
        """Evaluate a single rule."""
        check = rule.get("check", "")
        intent = context.get("intent", {})
        output = context.get("output", {})

        try:
            # Parse simple check expressions
            passed = self._run_check(check, intent, output)
            return RuleResult(rule, passed)
        except Exception as e:
            return RuleResult(rule, False, f"Check error: {str(e)}")

    def _run_check(self, check: str, intent: Dict, output: Dict) -> bool:
        """Run a check expression. Supports simple operators."""
        if not check:
            return True

        # Handle arrow notation (conditional)
        if " → " in check or " -> " in check:
            parts = re.split(r" ?→| -> ", check, 1)
            condition = parts[0].strip()
            # If condition is met, then evaluate consequence
            if self._eval_simple(condition, intent, output):
                if len(parts) > 1:
                    return self._eval_simple(parts[1].strip(), intent, output)
            return True  # Condition not met = rule passes

        return self._eval_simple(check, intent, output)

    def _eval_simple(self, expr: str, intent: Dict, output: Dict) -> bool:
        """Evaluate a simple expression."""
        expr = expr.strip()

        # null checks
        if expr.endswith("== true"):
            path = expr.replace("== true", "").strip()
            return self._get_value(path, intent, output) is not None
        if expr.endswith("== false"):
            path = expr.replace("== false", "").strip()
            return self._get_value(path, intent, output) is None
        if expr.endswith("!= null"):
            path = expr.replace("!= null", "").strip()
            return self._get_value(path, intent, output) is not None
        if expr.endswith("== null"):
            path = expr.replace("== null", "").strip()
            return self._get_value(path, intent, output) is None

        # Numeric comparisons
        for op in [">=", "<=", ">", "<", "==", "!="]:
            if op in expr:
                parts = expr.split(op, 1)
                path = parts[0].strip()
                try:
                    value = float(parts[1].strip())
                    actual = self._get_value(path, intent, output)
                    if actual is None:
                        return False
                    actual = float(actual) if not isinstance(actual, (int, float)) else actual
                    if op == ">=": return actual >= value
                    if op == "<=": return actual <= value
                    if op == ">": return actual > value
                    if op == "<": return actual < value
                    if op == "==": return actual == value
                    if op == "!=": return actual != value
                except (ValueError, TypeError):
                    return False

        # .length checks
        if ".length" in expr:
            for op in [">=", "<=", ">", "<", "==", "!="]:
                if op in expr:
                    parts = expr.split(op, 1)
                    path = parts[0].replace(".length", "").strip()
                    try:
                        value = int(parts[1].strip())
                        actual = self._get_value(path, intent, output)
                        if actual is None:
                            return False
                        length = len(actual) if isinstance(actual, (list, str, dict)) else 0
                        if op == ">=": return length >= value
                        if op == "<=": return length <= value
                        if op == ">": return length > value
                        if op == "<": return length < value
                        if op == "==": return length == value
                        if op == "!=": return length != value
                    except (ValueError, TypeError):
                        return False

        # Boolean: check if value exists and is truthy
        val = self._get_value(expr, intent, output)
        return val is not None and val is not False

    def _get_value(self, path: str, intent: Dict, output: Dict) -> Any:
        """Get a value from intent or output using dot notation."""
        # Try output first, then intent
        for source in [output, intent]:
            parts = path.split(".")
            val = source
            for p in parts:
                if isinstance(val, dict) and p in val:
                    val = val[p]
                elif isinstance(val, dict) and p.replace("_", "") in val:
                    val = val[p.replace("_", "")]
                else:
                    val = None
                    break
            if val is not None:
                return val
        return None


# ═══════════════════════════════════════════════════════════
# SCORING ENGINE
# ═══════════════════════════════════════════════════════════
class ScoringEngine:
    """Calculates weighted score from rule results."""

    def __init__(self, weights: Dict = CATEGORY_WEIGHTS):
        self.weights = weights

    def calculate(self, results: List[RuleResult]) -> Dict:
        """Calculate category scores + final weighted score."""
        category_scores = {}
        category_details = {}

        for category, weight in self.weights.items():
            cat_results = [r for r in results if r.category == category]
            if cat_results:
                passed = sum(1 for r in cat_results if r.passed)
                total = len(cat_results)
                score = passed / total
                category_scores[category] = round(score, 3)
                category_details[category] = {
                    "passed": passed,
                    "total": total,
                    "failed_ids": [r.id for r in cat_results if not r.passed]
                }
            else:
                category_scores[category] = 1.0
                category_details[category] = {"passed": 0, "total": 0, "failed_ids": []}

        # Weighted final score
        final_score = sum(
            category_scores.get(c, 0) * w
            for c, w in self.weights.items()
        )

        # Delegation score (critical for BiVOLT)
        delegation_rules = [r for r in results if r.action == "force_delegation"]
        delegation_passed = sum(1 for r in delegation_rules if r.passed)
        delegation_total = len(delegation_rules)
        delegation_score = delegation_passed / delegation_total if delegation_total > 0 else 1.0

        return {
            "final_score": round(final_score, 3),
            "category_scores": category_scores,
            "category_details": category_details,
            "delegation_score": round(delegation_score, 3),
            "total_rules": len(results),
            "passed_rules": sum(1 for r in results if r.passed),
            "failed_rules": sum(1 for r in results if not r.passed),
            "threshold": self._get_threshold(final_score),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def _get_threshold(self, score: float) -> str:
        """Determine action based on score thresholds."""
        if score >= THRESHOLDS["approve"]:
            return "approved"
        elif score >= THRESHOLDS["warn"]:
            return "approved_with_warnings"
        elif score >= THRESHOLDS["retry"]:
            return "retry_needed"
        else:
            return "rejected"


# ═══════════════════════════════════════════════════════════
# CONSTRAINT BUILDER (for LLM retry)
# ═══════════════════════════════════════════════════════════
def build_constraints(failed_results: List[RuleResult]) -> str:
    """Build constraint text for LLM retry based on failed rules."""
    if not failed_results:
        return ""

    constraints = []
    constraints.append("RULES VIOLATED — You MUST fix these before responding:")

    for r in failed_results:
        constraints.append(f"- [{r.id}] {r.name}: {r.rule}")
        if r.action == "force_delegation":
            constraints.append(f"  → DELEGATE to the appropriate system/agent. Do NOT respond with text.")
        elif r.action == "require_execution":
            constraints.append(f"  → Include a next_action with owner in your response.")
        elif r.action == "reject":
            constraints.append(f"  → This is MANDATORY. Your response will be rejected if not fixed.")
        elif r.action == "require_confirmation":
            constraints.append(f"  → Require human confirmation before proceeding.")

    constraints.append("\nFormat your response as JSON with these fields: sku_ready, next_action, metrics")
    return "\n".join(constraints)


# ═══════════════════════════════════════════════════════════
# MAIN EVALUATE FUNCTION (used by BOLT API)
# ═══════════════════════════════════════════════════════════
def evaluate(intent: Dict, output: Dict) -> Dict:
    """
    Main evaluation function. Called by BOLT API after LLM response.

    Returns: {
        "valid": bool,
        "score": 0.0-1.0,
        "threshold": str,
        "category_scores": {...},
        "delegation_score": 0.0-1.0,
        "failed_rules": [...],
        "constraints": str (for retry),
        "next_action": {...}
    }
    """
    start = time.time()

    loader = RuleLoader()
    evaluator = RuleEvaluator(loader)
    scorer = ScoringEngine()

    results = evaluator.evaluate(intent, output)
    score = scorer.calculate(results)

    failed = [r for r in results if not r.passed]
    constraints = build_constraints(failed)

    elapsed_ms = (time.time() - start) * 1000

    # Save score
    score_id = f"score-{int(time.time())}"
    score_file = SCORES_DIR / f"{score_id}.json"
    score_data = {
        "id": score_id,
        "score": score,
        "failed_rules": [{"id": r.id, "name": r.name, "action": r.action} for r in failed],
        "intent_summary": str(intent.get("intent", ""))[:200] if intent else "",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    with open(score_file, "w") as f:
        json.dump(score_data, f, indent=2)

    return {
        "valid": score["threshold"] in ["approved", "approved_with_warnings"],
        "score": score["final_score"],
        "delegation_score": score["delegation_score"],
        "threshold": score["threshold"],
        "category_scores": score["category_scores"],
        "total_rules": score["total_rules"],
        "passed_rules": score["passed_rules"],
        "failed_rules": [{"id": r.id, "name": r.name, "category": r.category, "action": r.action} for r in failed],
        "constraints": constraints if failed else "",
        "evaluation_ms": round(elapsed_ms, 1),
        "next_action": output.get("next_action", {}) if score["threshold"] != "rejected" else None
    }


# ═══════════════════════════════════════════════════════════
# CLI / TEST
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    # Test with sample data
    intent = {
        "intent": "crear sistema de cotizaciones automatizadas",
        "lead_score": 95,
        "product": "CLAWBOT"
    }

    output = {
        "title": "Sistema de Cotizaciones Automatizadas",
        "sku_ready": True,
        "sku": {
            "name": "Sistema de Cotizaciones Automatizadas",
            "includes": ["ClickUp setup", "Automatización n8n", "Dashboard"],
            "price_model": "setup + mensual"
        },
        "metrics": {"defined": True, "time_reduction": 0.6},
        "next_action": {"task": "Agendar demo", "owner": "admin", "deadline": "2026-04-15"},
        "revenue_potential": 0.95,
        "workflow": {"states": ["lead", "cotizado", "cerrado"]}
    }

    result = evaluate(intent, output)
    print(f"\n{'='*50}")
    print(f"  BRF Evaluation Result")
    print(f"{'='*50}")
    print(f"  Score: {result['score']}")
    print(f"  Delegation: {result['delegation_score']}")
    print(f"  Threshold: {result['threshold']}")
    print(f"  Rules: {result['passed_rules']}/{result['total_rules']} passed")
    print(f"  Time: {result['evaluation_ms']}ms")
    if result['failed_rules']:
        print(f"\n  Failed rules:")
        for r in result['failed_rules']:
            print(f"    ❌ {r['id']}: {r['name']} ({r['action']})")
    else:
        print(f"\n  ✅ All rules passed!")
