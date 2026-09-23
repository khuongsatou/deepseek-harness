#!/usr/bin/env python3
"""
Automated smoke test suite for JEV Usage Router.
Validates:
1. Prerequisite & setup checks
2. Shadow mode routing & logging
3. Kill switch (bypass flag & config)
4. Flip to Active mode
5. Active execution instructions
6. Irreversible action protection (Human-in-the-loop guard)
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
SKILL_SCRIPTS = ROOT_DIR / ".agents" / "skills" / "jev-usage-router" / "scripts"
CONFIG_FILE = ROOT_DIR / ".jev" / "config.json"
LOG_FILE = ROOT_DIR / ".jev" / "logs" / "router.jsonl"


def run_cmd(cmd_list):
    res = subprocess.run(cmd_list, cwd=ROOT_DIR, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"FAILED: {' '.join(cmd_list)}")
        print(f"Stdout: {res.stdout}")
        print(f"Stderr: {res.stderr}")
        sys.exit(1)
    return res.stdout.strip()


def run_json(cmd_list):
    out = run_cmd(cmd_list)
    try:
        return json.loads(out)
    except Exception as e:
        print(f"Failed to parse JSON output: {e}\nRaw output:\n{out}")
        sys.exit(1)


def test_section(title):
    print(f"\n👉 [TEST] {title}")


def main():
    print("=" * 65)
    print("       JEV USAGE ROUTER - AUTOMATED SMOKE TEST SUITE")
    print("=" * 65)

    # 1. Setup & Prerequisite Check
    test_section("1. Checking Setup Prerequisites (setup_jev.sh --check)")
    setup_out = run_cmd(["bash", str(SKILL_SCRIPTS / "setup_jev.sh"), "--check"])
    assert "Prerequisites verified successfully" in setup_out
    print("  ✅ Prerequisites verified (uv, python3, git).")

    # 2. Reset config to clean shadow state
    test_section("2. Resetting Router to SHADOW mode")
    run_cmd(["python3", str(SKILL_SCRIPTS / "flip_mode.py"), "bypass", "off"])
    run_cmd(["python3", str(SKILL_SCRIPTS / "flip_mode.py"), "shadow"])
    status = run_cmd(["python3", str(SKILL_SCRIPTS / "flip_mode.py"), "status"])
    assert "Current Mode:            SHADOW" in status
    assert "Disengaged" in status
    print("  ✅ Router set to SHADOW mode, bypass disengaged.")

    # 3. Test Shadow Routing across 4 core intents
    test_section("3. Testing Shadow Mode Routing across 4 core intents")

    # Browser intent -> fast JEV
    res = run_json(["python3", str(SKILL_SCRIPTS / "route.py"), "--intent", "browser", "--context", "Search flight from SFO to JFK on Google Flights"])
    assert res["route"] == "browser_fast_jev"
    assert res["mode"] == "shadow"
    assert res["execution_instruction"] == "SHADOW_OBSERVATION_ONLY_PROCEED_WITH_HARNESS_BASELINE"
    print(f"  ✅ Browser (Interactive) -> {res['route']} ({res['elapsed_ms']}ms)")

    # Browser intent -> targeted read (static)
    res = run_json(["python3", str(SKILL_SCRIPTS / "route.py"), "--intent", "browser", "--context", "Extract text and read documentation from https://docs.example.com"])
    assert res["route"] == "targeted_read"
    print(f"  ✅ Browser (Static text) -> {res['route']} ({res['elapsed_ms']}ms)")

    # Research intent -> direct search
    res = run_json(["python3", str(SKILL_SCRIPTS / "route.py"), "--intent", "research", "--context", "Quick lookup of python version compatibility"])
    assert res["route"] == "search_direct"
    print(f"  ✅ Research (Quick lookup) -> {res['route']} ({res['elapsed_ms']}ms)")

    # Retry intent -> in-turn retry
    res = run_json(["python3", str(SKILL_SCRIPTS / "route.py"), "--intent", "retry", "--context", "Request timed out with 503 service unavailable"])
    assert res["route"] == "in_turn_retry"
    print(f"  ✅ Retry (Transient timeout) -> {res['route']} ({res['elapsed_ms']}ms)")

    # Subagent intent -> reject trivial bot spawn
    res = run_json(["python3", str(SKILL_SCRIPTS / "route.py"), "--intent", "subagent", "--context", "Quick check of syntax in one file"])
    assert res["route"] == "reject_subagent_run_in_main"
    print(f"  ✅ Subagent (Trivial edit) -> {res['route']} ({res['elapsed_ms']}ms)")

    # 4. Test Kill Switch (Bypass)
    test_section("4. Testing Kill Switch (Bypass on/off)")
    # CLI flag test
    res = run_json(["python3", str(SKILL_SCRIPTS / "route.py"), "--bypass", "--intent", "browser", "--context", "Any task"])
    assert res["bypassed"] is True
    assert res["mode"] == "bypass"
    print("  ✅ CLI flag --bypass instantly returns bypassed: true.")

    # Config bypass toggle test
    run_cmd(["python3", str(SKILL_SCRIPTS / "flip_mode.py"), "bypass", "on"])
    res = run_json(["python3", str(SKILL_SCRIPTS / "route.py"), "--intent", "browser", "--context", "Any task"])
    assert res["bypassed"] is True
    print("  ✅ Config kill switch ('bypass on') successfully engages bypass.")

    run_cmd(["python3", str(SKILL_SCRIPTS / "flip_mode.py"), "bypass", "off"])
    res = run_json(["python3", str(SKILL_SCRIPTS / "route.py"), "--intent", "browser", "--context", "Search Google Flights"])
    assert res["bypassed"] is False
    print("  ✅ Config kill switch ('bypass off') successfully disengages bypass.")

    # 5. Flip Active Mode
    test_section("5. Testing Flip to ACTIVE Mode ('deepseek harness nghe route · Jev quyết · harness execute')")
    run_cmd(["python3", str(SKILL_SCRIPTS / "flip_mode.py"), "active"])
    status = run_cmd(["python3", str(SKILL_SCRIPTS / "flip_mode.py"), "status"])
    assert "Current Mode:            ACTIVE" in status
    print("  ✅ Flipped mode to ACTIVE.")

    # Active test for safe action
    res = run_json(["python3", str(SKILL_SCRIPTS / "route.py"), "--intent", "browser", "--context", "Read article overview"])
    assert res["mode"] == "active"
    assert res["is_irreversible"] is False
    assert res["execution_instruction"] == "PROCEED_WITH_RECOMMENDED_ROUTE"
    print(f"  ✅ Active Reversible Action -> {res['route']} | Instruction: {res['execution_instruction']}")

    # 6. Irreversible Action Protection ("Việc irreversible thì người vẫn giữ nút")
    test_section("6. Testing Irreversible Action Safety ('Người vẫn giữ nút')")
    # Payment / booking action
    res = run_json(["python3", str(SKILL_SCRIPTS / "route.py"), "--intent", "browser", "--context", "Checkout flight and pay with credit card"])
    assert res["is_irreversible"] is True
    assert res["require_human_confirmation"] is True
    assert res["execution_instruction"] == "HUMAN_CONFIRMATION_REQUIRED"
    print(f"  ✅ Irreversible Payment -> {res['human_confirmation_reason']}")
    print(f"     Execution Instruction: {res['execution_instruction']} (Human-in-the-loop enforced)")

    # Destructive git push action
    res = run_json(["python3", str(SKILL_SCRIPTS / "route.py"), "--intent", "subagent", "--context", "Execute git push --force origin main and delete branches"])
    assert res["is_irreversible"] is True
    assert res["require_human_confirmation"] is True
    assert res["execution_instruction"] == "HUMAN_CONFIRMATION_REQUIRED"
    print(f"  ✅ Irreversible Git Force Push -> {res['human_confirmation_reason']}")
    print(f"     Execution Instruction: {res['execution_instruction']} (Human-in-the-loop enforced)")

    # 7. Check Log Inspector
    test_section("7. Testing Log Inspector Output")
    inspect_out = run_cmd(["python3", str(SKILL_SCRIPTS / "inspect_logs.py"), "--tail", "5"])
    assert "JEV USAGE ROUTER - SHADOW LOG SUMMARY" in inspect_out
    assert "System-1 speed" in inspect_out
    print("  ✅ Log inspector parsed telemetry and generated status summary successfully.")

    # Reset back to shadow mode for safe user onboarding
    run_cmd(["python3", str(SKILL_SCRIPTS / "flip_mode.py"), "shadow"])

    print("\n" + "=" * 65)
    print("   🎉 ALL 7 SMOKE TESTS PASSED! JEV ROUTER IS FULLY OPERATIONAL.")
    print("=" * 65)


if __name__ == "__main__":
    main()
