"""Pluck — CLI entry point.

Examples:
    python main.py --gui
    python main.py --url "https://example.com/products" --engine local
    python main.py --url "..." --engine claude --api-key sk-ant-...
    python main.py --url "..." --engine gemini --api-key ...
    python main.py --url "..." --engine ollama --model llava:7b
    python main.py --url "..." -i "extract size, color, material"
    python main.py --mint-key PRO --days 365
    python main.py --activate PRO-2027...
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from extractor import PluckExtractor
from subscription import (
    LicenseManager,
    Plan,
    UsageTracker,
    can_extract,
    clamp_max_products,
    generate_key,
    plan_info,
)

load_dotenv()


def _print_progress(msg: str) -> None:
    print(f"[*] {msg}", flush=True)


ENGINE_ENV_KEY = {
    "claude": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


def cli() -> int:
    parser = argparse.ArgumentParser(
        description="Pluck — AI-powered product scraper for any shopping page",
    )
    parser.add_argument("--url", help="Shopping page URL to extract")
    parser.add_argument("--max-products", type=int, default=20)
    parser.add_argument("--output", default="output")
    parser.add_argument("--no-headless", action="store_true", help="Show browser window")
    parser.add_argument(
        "--engine",
        default="local",
        choices=["local", "claude", "openai", "gemini", "ollama"],
        help="AI engine. 'local' runs fully on-device with no API key.",
    )
    parser.add_argument("--model", default=None, help="Override default model for the engine")
    parser.add_argument(
        "--api-key", default=None,
        help="API key for cloud engines (or use the engine's env var)",
    )
    parser.add_argument(
        "--instructions", "-i", default=None,
        help="Extra instructions for the LLM (e.g. 'extract size, color, material')",
    )
    parser.add_argument("--gui", action="store_true", help="Launch GUI")

    parser.add_argument("--mint-key", choices=["PRO", "TEAM"])
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--activate", metavar="KEY")
    parser.add_argument("--plan-status", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.mint_key:
        key = generate_key(Plan(args.mint_key), days=args.days)
        print(key)
        return 0

    if args.activate:
        mgr = LicenseManager()
        lic = mgr.activate(args.activate)
        if not lic:
            print("[!] Invalid or expired license key.", file=sys.stderr)
            return 2
        print(f"[*] Activated {plan_info(lic.plan)['label']} — expires {lic.expires_at}")
        return 0

    if args.plan_status:
        mgr = LicenseManager()
        lic = mgr.load()
        used = UsageTracker().today()
        info = plan_info(lic.plan)
        limit = info["daily_limit"]
        usage = f"{used}/{limit}" if limit is not None else f"{used} (unlimited)"
        print(f"Plan       : {info['label']}")
        print(f"Expires    : {lic.expires_at}")
        print(f"Usage today: {usage}")
        return 0

    if args.gui:
        from gui import launch_gui
        launch_gui()
        return 0

    if not args.url:
        parser.error("--url or --gui is required")

    mgr = LicenseManager()
    lic = mgr.load()
    usage = UsageTracker()
    ok, reason = can_extract(lic.plan, usage.today())
    if not ok:
        print(f"[!] {reason}", file=sys.stderr)
        print("    Use --mint-key PRO to generate a demo Pro key, then --activate <key>.",
              file=sys.stderr)
        return 3

    info = plan_info(lic.plan)
    requested = args.max_products
    capped = clamp_max_products(lic.plan, requested)
    if capped < requested:
        print(f"[*] Capped to {capped} products ({info['label']} plan limit).")

    instructions = args.instructions
    if instructions and not info["custom_instructions"]:
        print("[!] Custom instructions require Pro or Team. Ignoring --instructions.",
              file=sys.stderr)
        instructions = None

    api_key = args.api_key
    if args.engine in ENGINE_ENV_KEY and not api_key:
        api_key = os.getenv(ENGINE_ENV_KEY[args.engine])
        if not api_key:
            print(
                f"[!] {ENGINE_ENV_KEY[args.engine]} is not set. "
                "Pass --api-key or use --engine local for free local extraction.",
                file=sys.stderr,
            )
            return 2

    extractor = PluckExtractor(
        output_dir=Path(args.output),
        max_products=capped,
        headless=not args.no_headless,
        engine=args.engine,
        api_key=api_key,
        model=args.model,
        progress_cb=_print_progress,
        custom_instructions=instructions,
    )
    result = extractor.run_sync(args.url)
    usage.increment()
    print(f"\nExtracted {len(result.products)} product(s) → {result.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
