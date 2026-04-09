#!/usr/bin/env python3
"""
SmarterBOT Rule Tuner — Feedback Loop
════════════════════════════════════════
Analyzes historical evaluation scores.
Auto-adjusts rule weights based on pass rates.
Saves tuning decisions for audit trail.

Deploy: /opt/smarterbot/rule-tuner.py
Cron: Every 12 hours
"""

import os
import json
import time
import httpx
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════
BASE_DIR = Path(__file__).parent
RULES_DIR = BASE_DIR / "rules"
SCORES_DIR = BASE_DIR / "rule-scores"
TUNING_LOG = BASE_DIR / "tuning-log.json"
VOLT_URL = "http://127.0.0.1:9011"
TG_BOT = os.getenv("TELEGRAM_BOT_TOKEN", "7631713367:AAFCRvqzBqHT1z10JQ8ez0YFFrNfYHbxybc")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6683244662")

# Tuning parameters
MIN_WEIGHT = 0.01
MAX_WEIGHT = 0.20
TUNING_RATE = 0.10  # 10% adjustment per cycle
MIN_SAMPLES = 3  # Minimum evaluations before tuning

# ═══════════════════════════════════════════════════════════
# LOADER
# ═══════════════════════════════════════════════════════════
def load_rules():
    """Load all rules from JSON files."""
    rules = {}
    for f in RULES_DIR.glob("*.json"):
        if f.name in ("registry.json", "schema.json"):
            continue
        try:
            with open(f) as fh:
                for r in json.load(fh):
                    rules[r["id"]] = r
        except Exception as e:
            print(f"  ⚠️ Failed to load {f}: {e}")
    return rules

def save_rules(rules):
    """Save rules back to JSON files, grouped by category."""
    by_category = defaultdict(list)
    for r in rules.values():
        by_category[r["category"]].append(r)
    
    for category, cat_rules in by_category.items():
        fpath = RULES_DIR / f"{category}.json"
        with open(fpath, "w") as f:
            json.dump(cat_rules, f, indent=2)
    print(f"  ✅ Saved {len(rules)} rules")

def load_scores(hours: int = 48) -> list:
    """Load evaluation scores from last N hours."""
    if not SCORES_DIR.exists():
        return []
    
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    scores = []
    
    for f in SCORES_DIR.glob("*.json"):
        try:
            with open(f) as fh:
                s = json.load(fh)
                ts = s.get("timestamp", "")
                if ts:
                    score_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if score_time >= cutoff:
                        scores.append(s)
        except Exception:
            pass
    
    scores.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return scores

# ═══════════════════════════════════════════════════════════
# TUNING ENGINE
# ═══════════════════════════════════════════════════════════
def analyze_scores(scores: list) -> dict:
    """Analyze score history to find patterns."""
    if not scores:
        return {"total": 0, "avg_score": 0, "pass_rate": 0}
    
    total = len(scores)
    def get_score_val(s):
        v = s.get("score", 0)
        if isinstance(v, dict):
            return v.get("final_score", 0)
        return v
    avg_score = sum(get_score_val(s) for s in scores) / total
    passed = sum(1 for s in scores if s.get("threshold") in ["approved", "approved_with_warnings"])
    
    # Category-level analysis
    category_stats = defaultdict(lambda: {"total": 0, "failed": 0})
    for s in scores:
        failed = s.get("failed_rules", [])
        for f in failed:
            cat = f.get("category", "unknown")
            category_stats[cat]["total"] += 1
            category_stats[cat]["failed"] += 1
    
    # Most failed rules
    rule_fail_count = defaultdict(int)
    for s in scores:
        for f in s.get("failed_rules", []):
            rule_fail_count[f["id"]] += 1
    
    most_failed = sorted(rule_fail_count.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "total": total,
        "avg_score": round(avg_score, 3),
        "pass_rate": round(passed / total, 3) if total > 0 else 0,
        "category_stats": dict(category_stats),
        "most_failed_rules": [{"id": r[0], "count": r[1]} for r in most_failed]
    }

def tune_rules(rules: dict, analysis: dict) -> list:
    """Adjust rule weights based on analysis."""
    changes = []
    
    if analysis["total"] < MIN_SAMPLES:
        return changes  # Not enough data
    
    # Find rules that fail consistently
    most_failed = analysis.get("most_failed_rules", [])
    
    for item in most_failed:
        rule_id = item["id"]
        fail_count = item["count"]
        fail_rate = fail_count / analysis["total"]
        
        if rule_id not in rules:
            continue
        
        rule = rules[rule_id]
        current_weight = rule.get("weight", 0.05)
        
        # If rule fails > 60% of the time, it might be too strict
        if fail_rate > 0.60:
            new_weight = max(MIN_WEIGHT, current_weight * (1 - TUNING_RATE))
            rule["weight"] = round(new_weight, 3)
            changes.append({
                "rule_id": rule_id,
                "action": "decreased",
                "reason": f"Fails {fail_rate:.0%} of time — may be too strict",
                "old_weight": current_weight,
                "new_weight": new_weight
            })
        
        # If rule never fails, it might be too lenient
        elif fail_rate < 0.05 and current_weight < 0.10:
            # Only increase if it's important
            if rule.get("severity") in ["critical", "high"]:
                new_weight = min(MAX_WEIGHT, current_weight * (1 + TUNING_RATE))
                rule["weight"] = round(new_weight, 3)
                changes.append({
                    "rule_id": rule_id,
                    "action": "increased",
                    "reason": f"Fails only {fail_rate:.0%} — may need more weight",
                    "old_weight": current_weight,
                    "new_weight": new_weight
                })
    
    return changes

def auto_disable_never_failing(rules: dict, analysis: dict, threshold: int = 50):
    """Optionally disable rules that never fail after many evaluations."""
    changes = []
    
    if analysis["total"] < threshold:
        return changes
    
    rule_fail_count = defaultdict(int)
    for s in analysis.get("most_failed_rules", []):
        rule_fail_count[s["id"]] = s["count"]
    
    for rule_id, rule in rules.items():
        if not rule.get("enabled", True):
            continue
        
        fails = rule_fail_count.get(rule_id, 0)
        if fails == 0 and analysis["total"] >= threshold:
            # Rule never triggered in 50+ evaluations
            # Don't disable, just warn
            changes.append({
                "rule_id": rule_id,
                "action": "flagged_unused",
                "reason": f"Never failed in {analysis['total']} evaluations"
            })
    
    return changes

# ═══════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════
def save_tuning_log(tuning_session: dict):
    """Save tuning session to log."""
    try:
        with open(TUNING_LOG) as f:
            log = json.load(f)
    except:
        log = {"sessions": []}
    
    log["sessions"].insert(0, tuning_session)
    log["sessions"] = log["sessions"][:50]  # Keep last 50
    
    with open(TUNING_LOG, "w") as f:
        json.dump(log, f, indent=2, default=str)

# ═══════════════════════════════════════════════════════════
# REPORTING
# ═══════════════════════════════════════════════════════════
async def send_telegram(msg):
    """Send message to Telegram."""
    if not TG_BOT or not TG_CHAT:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(f"https://api.telegram.org/bot{TG_BOT}/sendMessage",
                json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"})
        return True
    except:
        return False

def report_to_volt(tuning_session: dict):
    """Report tuning results to Volt bridge."""
    try:
        httpx.post(f"{VOLT_URL}/api/agent/sync", json={
            "action": "daily_report",
            "agent": "rule-tuner",
            "report": tuning_session,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, timeout=10)
        return True
    except:
        return False

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
def run_tuning():
    """Run the full tuning cycle."""
    print(f"🔧 Rule Tuner — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}", flush=True)
    
    # 1. Load data
    rules = load_rules()
    scores = load_scores(hours=48)
    
    print(f"  Rules: {len(rules)}")
    print(f"  Scores (48h): {len(scores)}")
    
    # 2. Analyze
    analysis = analyze_scores(scores)
    print(f"  Avg score: {analysis['avg_score']}")
    print(f"  Pass rate: {analysis['pass_rate']}")
    
    # 3. Tune
    changes = tune_rules(rules, analysis)
    unused = auto_disable_never_failing(rules, analysis)
    
    all_changes = changes + unused
    
    # 4. Save if changed
    if all_changes:
        save_rules(rules)
        print(f"  Changes: {len(all_changes)}")
        for c in all_changes:
            print(f"    {c['rule_id']}: {c['action']} ({c.get('reason', '')})")
    else:
        print(f"  No changes needed")
    
    # 5. Log
    tuning_session = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scores_analyzed": len(scores),
        "analysis": analysis,
        "changes": all_changes,
        "rules_touched": len(rules)
    }
    save_tuning_log(tuning_session)
    
    # 6. Report to Volt
    report_to_volt(tuning_session)
    
    # 7. Telegram alert if significant changes
    if len(changes) >= 3:
        import asyncio
        msg = (
            f"🔧 <b>Rule Tuning Alert</b>\n\n"
            f"Analyzed: {len(scores)} evaluations\n"
            f"Avg Score: {analysis['avg_score']}\n"
            f"Changes: {len(changes)} rules adjusted\n\n"
            + "\n".join(f"• {c['rule_id']}: {c['action']}" for c in changes[:5])
        )
        asyncio.get_event_loop().run_until_complete(send_telegram(msg))
    
    print(f"  ✅ Tuning complete", flush=True)
    return tuning_session

if __name__ == "__main__":
    run_tuning()
