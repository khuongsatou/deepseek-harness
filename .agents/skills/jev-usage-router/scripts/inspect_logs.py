#!/usr/bin/env python3
"""
Inspect and analyze JEV router logs.
Allows inspecting shadow-mode logs, verifying confidence and latency,
and determining whether the router is ready to flip to active mode.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
CONFIG_FILE = ROOT_DIR / ".jev" / "config.json"
DEFAULT_LOG_FILE = ROOT_DIR / ".jev" / "logs" / "router.jsonl"


def load_logs(log_file: Path):
    if not log_file.exists():
        return []
    entries = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
    return entries


def main():
    parser = argparse.ArgumentParser(description="Inspect JEV router logs")
    parser.add_argument("--tail", type=int, default=10, help="Number of recent entries to show (default: 10)")
    parser.add_argument("--json", action="store_true", help="Output summary as JSON")
    args = parser.parse_args()

    # Find log file from config if available
    log_file = DEFAULT_LOG_FILE
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                conf = json.load(f)
                rel_path = conf.get("log_path", ".jev/logs/router.jsonl")
                log_file = ROOT_DIR / rel_path
        except Exception:
            pass

    entries = load_logs(log_file)
    total = len(entries)

    if total == 0:
        print(f"No router logs found at {log_file}")
        print("Run the router in shadow mode to collect evaluation telemetry.")
        return

    intent_counts = Counter(e.get("intent", "unknown") for e in entries)
    route_counts = Counter(e.get("route", "unknown") for e in entries)
    mode_counts = Counter(e.get("mode", "unknown") for e in entries)
    latencies = [e.get("elapsed_ms", 0.0) for e in entries if "elapsed_ms" in e]
    confidences = [e.get("confidence", 0.0) for e in entries if "confidence" in e]
    irreversibles = sum(1 for e in entries if e.get("is_irreversible", False))

    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    avg_conf = round((sum(confidences) / len(confidences)) * 100, 1) if confidences else 0.0

    summary = {
        "total_records": total,
        "modes": dict(mode_counts),
        "intents": dict(intent_counts),
        "routes": dict(route_counts),
        "avg_latency_ms": avg_latency,
        "avg_confidence_pct": avg_conf,
        "irreversible_actions_detected": irreversibles,
        "readiness": "READY" if total >= 3 and avg_conf >= 85.0 else "COLLECT_MORE_SHADOW_RUNS"
    }

    if args.json:
        print(json.dumps(summary, indent=2))
        return

    print("=" * 65)
    print("           JEV USAGE ROUTER - SHADOW LOG SUMMARY")
    print("=" * 65)
    print(f"Log path:          {log_file}")
    print(f"Total decisions:   {total}")
    print(f"Average latency:   {avg_latency} ms (System-1 speed)")
    print(f"Mean confidence:   {avg_conf}%")
    print(f"Irreversible tags: {irreversibles} (guarded for human confirmation)")
    print("-" * 65)

    print("Breakdown by Intent:")
    for intent, count in intent_counts.most_common():
        print(f"  • {intent:<16}: {count:>3} ({count/total*100:.1f}%)")

    print("\nBreakdown by Recommended Route:")
    for route, count in route_counts.most_common():
        print(f"  • {route:<28}: {count:>3} ({count/total*100:.1f}%)")

    print("\nBreakdown by Mode:")
    for mode, count in mode_counts.most_common():
        print(f"  • {mode:<16}: {count:>3} ({count/total*100:.1f}%)")

    print("-" * 65)
    if summary["readiness"] == "READY":
        print("STATUS: [READY TO FLIP ACTIVE] - Decisions are stable and high-confidence.")
        print("To flip active: python3 .agents/skills/jev-usage-router/scripts/flip_mode.py active")
    else:
        print("STATUS: [SHADOW OBSERVATION] - Continue running to accumulate more telemetry.")
    print("-" * 65)

    recent = entries[-args.tail:]
    print(f"\nLast {len(recent)} Router Events:")
    for i, e in enumerate(recent, 1):
        ts = e.get("timestamp", "").split("T")[-1][:8]
        intent = e.get("intent", "-")
        route = e.get("route", "-")
        conf = int(e.get("confidence", 0) * 100)
        mode = e.get("mode", "-")
        snippet = e.get("context_snippet", "")[:45]
        irrev = " [IRREVERSIBLE]" if e.get("is_irreversible") else ""
        print(f" [{ts}] ({mode}) {intent} -> {route} ({conf}% conf){irrev}")
        print(f"         Context: {snippet}")
    print("=" * 65)


if __name__ == "__main__":
    main()
