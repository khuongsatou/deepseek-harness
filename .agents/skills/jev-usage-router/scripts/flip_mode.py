#!/usr/bin/env python3
"""
CLI helper to inspect status and flip mode for JEV Usage Router.
Supports switching between 'shadow' and 'active', toggling the kill switch (bypass),
and checking current configuration.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
CONFIG_FILE = ROOT_DIR / ".jev" / "config.json"


def load_config():
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
            sys.stderr.write(f"[WARN] Error loading {CONFIG_FILE}: {e}\n")
    return defaults


def save_config(conf):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(conf, f, indent=2)
    print(f"Updated configuration saved to: {CONFIG_FILE}")


def main():
    parser = argparse.ArgumentParser(description="Flip mode and toggle kill switch for JEV router")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # mode command
    mode_parser = subparsers.add_parser("mode", help="Set router mode (shadow or active)")
    mode_parser.add_argument("target", choices=["shadow", "active"], help="Target mode")

    # direct active / shadow aliases
    subparsers.add_parser("active", help="Alias for: mode active")
    subparsers.add_parser("shadow", help="Alias for: mode shadow")

    # bypass / kill-switch command
    bypass_parser = subparsers.add_parser("bypass", help="Toggle kill switch (bypass)")
    bypass_parser.add_argument("state", choices=["on", "off", "status"], default="status", nargs="?", help="Kill switch state")

    # status command
    subparsers.add_parser("status", help="Show current router status")

    args = parser.parse_args()
    conf = load_config()

    cmd = args.command
    if not cmd or cmd == "status":
        print("=== JEV Router Status ===")
        print(f"Enabled:                 {conf.get('enabled')}")
        print(f"Current Mode:            {conf.get('mode').upper()}")
        print(f"Kill switch (Bypass):    {'ENGAGED (Bypassing JEV)' if conf.get('bypass') else 'Disengaged (Normal operation)'}")
        print(f"Irreversible Guard:      {'Active (Human-in-the-loop enabled)' if conf.get('require_human_confirmation_for_irreversible') else 'Disabled'}")
        print(f"Log path:                {conf.get('log_path')}")
        return

    if cmd in ("active", "shadow"):
        conf["mode"] = cmd
        save_config(conf)
        print(f"SUCCESS: Mode flipped to '{cmd.upper()}'.")
        if cmd == "active":
            print("Notice: DeepSeek Harness will now actively follow JEV routes.")
            print("        Irreversible operations remain strictly protected by human confirmation.")
        return

    if cmd == "mode":
        conf["mode"] = args.target
        save_config(conf)
        print(f"SUCCESS: Mode set to '{args.target.upper()}'.")
        return

    if cmd == "bypass":
        state = args.state
        if state == "on":
            conf["bypass"] = True
            save_config(conf)
            print("KILL SWITCH ENGAGED: JEV router is now completely bypassed.")
        elif state == "off":
            conf["bypass"] = False
            save_config(conf)
            print("KILL SWITCH DISENGAGED: JEV router is active/shadow per configuration.")
        else:
            print(f"Bypass state: {conf.get('bypass')}")
        return


if __name__ == "__main__":
    main()
