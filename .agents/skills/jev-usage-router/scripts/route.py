#!/usr/bin/env python3
"""
JEV Usage Router for DeepSeek Harness.
Evaluates proposed operations (browser, research, retry, subagent invocation)
and returns structured routing decisions with shadow/active modes, kill switch,
and human-in-the-loop protection for irreversible actions.
"""

import argparse
import datetime
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parents[4]
CONFIG_FILE = ROOT_DIR / ".jev" / "config.json"
DEFAULT_LOG_FILE = ROOT_DIR / ".jev" / "logs" / "router.jsonl"

IRREVERSIBLE_PATTERNS = [
    r"\b(git\s+push|force[-_]push)\b",
    r"\b(git\s+reset\s+--hard)\b",
    r"\b(rm\s+-rf|del\s+/f|unlink)\b",
    r"\b(drop\s+(database|table)|delete\s+from|truncate)\b",
    r"\b(payment|pay|checkout|purchase|buy|book\s+flight|charge)\b",
    r"\b(transfer\s+funds|credit[-_]card|cvv)\b",
    r"\b(publish|deploy\s+prod|deploy\s+production)\b",
    r"\b(delete[-_]user|destroy|format\s+disk)\b",
]


def load_config() -> Dict[str, Any]:
    defaults = {
        "enabled": True,
        "mode": "shadow",
        "bypass": False,
        "jev_dir": "external/jev-ultrafast",
        "log_path": ".jev/logs/router.jsonl",
        "require_human_confirmation_for_irreversible": True,
        "confidence_threshold": 0.75,
        "endpoints": {
            "jev_service_url": "http://127.0.0.1:8766"
        }
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                defaults.update(data)
        except Exception as e:
            sys.stderr.write(f"[WARN] Failed to read {CONFIG_FILE}: {e}\n")
    return defaults


def check_irreversible(context: str, intent: str) -> Tuple[bool, Optional[str]]:
    combined = f"{intent} {context}".lower()
    for pattern in IRREVERSIBLE_PATTERNS:
        match = re.search(pattern, combined)
        if match:
            return True, f"Detected irreversible pattern: '{match.group(0)}'"
    return False, None


def evaluate_decision(intent: str, context: str) -> Dict[str, Any]:
    """
    Evaluates the intent and context, returning a structured decision.
    Uses ultra-fast System-1 classification logic aligned with JEV principles.
    """
    ctx_lower = context.lower()
    intent_norm = intent.lower().strip()

    if intent_norm in ("browser", "web_browser", "browse"):
        # Determine if simple interactive, static fetch, or heavy CDP debug
        if any(w in ctx_lower for w in ["read", "extract text", "fetch article", "view documentation", "api spec", "static"]):
            return {
                "route": "targeted_read",
                "recommended_tool": "read_url_content",
                "action": "Use direct HTTP/Markdown extraction without launching a full browser",
                "confidence": 0.95,
                "reasoning": "Static or content-only goal does not require full DOM emulation or JS engine."
            }
        elif any(w in ctx_lower for w in ["flight", "booking", "form", "login", "search hotel", "interactive", "table", "click"]):
            return {
                "route": "browser_fast_jev",
                "recommended_tool": "jev_ultrafast_agent",
                "action": "Engage JEV ultrafast System-1 loop (atomic DOM snapshot + speculative fan-out heads)",
                "confidence": 0.92,
                "reasoning": "Interactive task benefits from sub-100ms speculative operation and target heads."
            }
        else:
            return {
                "route": "browser_harness_playwright",
                "recommended_tool": "browser_use_stagehand_or_playwright",
                "action": "Use deep Playwright/CDP browser harness",
                "confidence": 0.85,
                "reasoning": "Standard browser session with full DevTools capabilities."
            }

    elif intent_norm in ("research", "search", "investigate"):
        if any(w in ctx_lower for w in ["quick", "lookup", "definition", "error code", "version", "homepage"]):
            return {
                "route": "search_direct",
                "recommended_tool": "search_web",
                "action": "Execute single targeted query via search_web",
                "confidence": 0.94,
                "reasoning": "Direct factoid or lookup query is fastest with single search tool call."
            }
        elif any(w in ctx_lower for w in ["api doc", "gemini", "sdk reference", "method signature"]):
            return {
                "route": "targeted_doc_search",
                "recommended_tool": "mcp_gemini-api_gemini-api-docs_gemini_search_docs",
                "action": "Query official SDK / API documentation server directly",
                "confidence": 0.96,
                "reasoning": "API/SDK queries should query upstream type reference and documentation chunks directly."
            }
        else:
            return {
                "route": "subagent_delegate",
                "recommended_tool": "invoke_subagent(TypeName='research')",
                "action": "Delegate broad exploratory search to research subagent",
                "confidence": 0.88,
                "reasoning": "Broad research benefits from isolated subagent context to prevent parent context clutter."
            }

    elif intent_norm in ("retry", "loop", "rerun"):
        if any(w in ctx_lower for w in ["timeout", "temporary", "503", "rate limit", "429", "connection reset", "econnreset"]):
            return {
                "route": "in_turn_retry",
                "recommended_tool": "exponential_backoff_retry",
                "action": "Retry operation with brief backoff (200ms - 1000ms)",
                "confidence": 0.92,
                "reasoning": "Transient network or rate-limiting issue is likely to succeed on quick retry."
            }
        elif any(w in ctx_lower for w in ["stale", "element not found", "detached", "dom changed", "out of date"]):
            return {
                "route": "reground_state",
                "recommended_tool": "refresh_snapshot_or_view",
                "action": "Re-ground state: fetch fresh DOM / file snapshot before re-attempting action",
                "confidence": 0.95,
                "reasoning": "State assumption became stale; re-grounding state prevents repetitive failure."
            }
        else:
            return {
                "route": "abort_or_escalate",
                "recommended_tool": "escalate_to_planner",
                "action": "Stop retrying; analyze underlying failure or request clarification",
                "confidence": 0.89,
                "reasoning": "Repeated non-transient failure indicates logic/syntax flaw; further blind retries will burn budget."
            }

    elif intent_norm in ("subagent", "call_subagent", "invoke_subagent", "bot"):
        if any(w in ctx_lower for w in ["one-line", "quick", "trivial", "single file", "check syntax", "simple edit"]):
            return {
                "route": "reject_subagent_run_in_main",
                "recommended_tool": "direct_main_turn_execution",
                "action": "Do NOT spawn subagent; execute directly in current turn",
                "confidence": 0.96,
                "reasoning": "Small trivial tasks have high subagent orchestration overhead; run directly in turn."
            }
        else:
            return {
                "route": "approve_subagent",
                "recommended_tool": "invoke_subagent",
                "action": "Spawn subagent with focused role and prompt",
                "confidence": 0.90,
                "reasoning": "Task contains substantial scope suitable for parallel or isolated subagent context."
            }

    else:
        return {
            "route": "standard_execution",
            "recommended_tool": "default_turn_tool",
            "action": "Proceed with default DeepSeek Harness behavior",
            "confidence": 0.80,
            "reasoning": f"Intent '{intent}' does not require specialized routing."
        }


def log_decision(log_path: Path, entry: Dict[str, Any]) -> None:
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        sys.stderr.write(f"[WARN] Failed to write router log to {log_path}: {e}\n")


def main():
    start_time = time.perf_counter()

    parser = argparse.ArgumentParser(description="JEV Usage Router for DeepSeek Harness")
    parser.add_argument("--intent", required=True, help="Action category: browser, research, retry, subagent")
    parser.add_argument("--context", required=True, help="Task description, goal, query or error message")
    parser.add_argument("--mode", choices=["shadow", "active", "auto"], default="auto", help="Execution mode override")
    parser.add_argument("--bypass", action="store_true", help="Kill switch: bypass JEV router")
    parser.add_argument("--json", action="store_true", default=True, help="Output as JSON (default)")

    args = parser.parse_args()
    config = load_config()

    # 1. Kill switch checks
    is_bypassed = (
        args.bypass
        or os.environ.get("JEV_BYPASS", "").lower() in ("1", "true", "yes")
        or config.get("bypass", False)
        or not config.get("enabled", True)
    )

    if is_bypassed:
        output = {
            "bypassed": True,
            "reason": "Kill switch engaged (via CLI flag, JEV_BYPASS env, or enabled=false)",
            "intent": args.intent,
            "route": "harness_default",
            "action": "Bypass JEV router and proceed with unguided harness execution",
            "mode": "bypass",
            "is_irreversible": False,
            "require_human_confirmation": False,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        print(json.dumps(output, indent=2 if args.json else None))
        sys.exit(0)

    # 2. Determine mode (shadow vs active)
    env_mode = os.environ.get("JEV_MODE", "").lower()
    if args.mode != "auto":
        mode = args.mode
    elif env_mode in ("shadow", "active"):
        mode = env_mode
    else:
        mode = config.get("mode", "shadow")

    # 3. Check for irreversible actions (human-in-the-loop invariant)
    is_irreversible, irreversible_reason = check_irreversible(args.context, args.intent)
    require_human = is_irreversible and config.get("require_human_confirmation_for_irreversible", True)

    # 4. Evaluate route decision
    decision = evaluate_decision(args.intent, args.context)
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # 5. Prepare final response
    response: Dict[str, Any] = {
        "bypassed": False,
        "mode": mode,
        "decision_source": "jev_ultrafast_router",
        "intent": args.intent,
        "context_snippet": args.context[:120] + ("..." if len(args.context) > 120 else ""),
        "route": decision["route"],
        "recommended_tool": decision["recommended_tool"],
        "action": decision["action"],
        "reasoning": decision["reasoning"],
        "confidence": decision["confidence"],
        "is_irreversible": is_irreversible,
        "require_human_confirmation": require_human,
        "human_confirmation_reason": irreversible_reason if require_human else None,
        "elapsed_ms": elapsed_ms,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    # In active mode: JEV decides, harness executes.
    # In shadow mode: JEV logs suggestion for observation, harness continues baseline.
    if mode == "active":
        response["execution_instruction"] = (
            "HUMAN_CONFIRMATION_REQUIRED" if require_human else "PROCEED_WITH_RECOMMENDED_ROUTE"
        )
    else:
        response["execution_instruction"] = "SHADOW_OBSERVATION_ONLY_PROCEED_WITH_HARNESS_BASELINE"

    # 6. Log decision
    log_rel_path = config.get("log_path", ".jev/logs/router.jsonl")
    log_file = ROOT_DIR / log_rel_path
    log_decision(log_file, response)

    print(json.dumps(response, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
