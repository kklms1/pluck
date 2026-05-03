"""Subscription, license, and usage tracking.

Demo-grade: license keys are HMAC-signed locally so users can't trivially
forge a higher tier by editing license.json. In a real product, signing
would happen on a license server (Stripe + your backend) and validation
would call out to that server.

Keys look like:  PRO-20271201-A1B2-c3d4e5f6789a
                 ^^^   ^^^^^^^^   ^^^^   ^^^^^^^^^^^^
                 plan  expiry     rand   12-hex HMAC sig
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import string
from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path

# Demo signing secret. In production this would only exist server-side.
_SECRET = b"shopping-extractor-demo-secret-v1-2026"

LICENSE_DIR = Path.home() / ".shopping-extractor"
LICENSE_PATH = LICENSE_DIR / "license.json"
USAGE_PATH = LICENSE_DIR / "usage.json"


class Plan(str, Enum):
    FREE = "FREE"
    PRO = "PRO"
    TEAM = "TEAM"


PLAN_INFO: dict[Plan, dict] = {
    Plan.FREE: {
        "label": "Free",
        "price": "$0",
        "period": "forever",
        "tagline": "Try it out",
        "features": [
            "5 extractions per day",
            "Up to 10 products per run",
            "Standard fields (name / price / discount)",
            "Single URL at a time",
        ],
        "daily_limit": 5,
        "max_products": 10,
        "custom_instructions": False,
        "batch": False,
        "checkout_url": None,
    },
    Plan.PRO: {
        "label": "Pro",
        "price": "$9.99",
        "period": "per month",
        "tagline": "For power users",
        "features": [
            "Unlimited extractions",
            "Up to 50 products per run",
            "Custom LLM instructions",
            "Priority Vision throughput",
        ],
        "daily_limit": None,
        "max_products": 50,
        "custom_instructions": True,
        "batch": False,
        "checkout_url": "https://buy.stripe.com/demo_pro",
    },
    Plan.TEAM: {
        "label": "Team",
        "price": "$29.99",
        "period": "per month",
        "tagline": "For teams & agencies",
        "features": [
            "Everything in Pro",
            "Up to 200 products per run",
            "Batch URL processing",
            "API access (coming soon)",
        ],
        "daily_limit": None,
        "max_products": 200,
        "custom_instructions": True,
        "batch": True,
        "checkout_url": "https://buy.stripe.com/demo_team",
    },
}


@dataclass
class License:
    plan: Plan
    expires_at: str   # ISO YYYY-MM-DD
    key: str

    def is_valid(self) -> bool:
        if self.plan == Plan.FREE:
            return True
        try:
            exp = datetime.strptime(self.expires_at, "%Y-%m-%d").date()
        except ValueError:
            return False
        return exp >= date.today()


def _sign(payload: str) -> str:
    return hmac.new(_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest()[:12]


def generate_key(plan: Plan, days: int = 365) -> str:
    """Mint a demo license key (used by `python main.py --mint-key PRO`)."""
    if plan == Plan.FREE:
        return "FREE"
    expires = date.fromordinal(date.today().toordinal() + days)
    expires_str = expires.strftime("%Y%m%d")
    rand = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
    payload = f"{plan.value}-{expires_str}-{rand}"
    sig = _sign(payload)
    return f"{payload}-{sig}"


def parse_key(key: str) -> License | None:
    """Parse + verify a license key. Returns None if invalid or tampered."""
    raw = (key or "").strip().upper()
    if raw == "FREE":
        return License(plan=Plan.FREE, expires_at="2099-12-31", key="FREE")
    parts = raw.split("-")
    if len(parts) != 4:
        return None
    plan_str, expires_str, rand, sig = parts
    try:
        plan = Plan(plan_str)
    except ValueError:
        return None
    payload = f"{plan_str}-{expires_str}-{rand}"
    if not hmac.compare_digest(_sign(payload).lower(), sig.lower()):
        return None
    try:
        expires_iso = datetime.strptime(expires_str, "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return None
    return License(plan=plan, expires_at=expires_iso, key=raw)


def plan_info(plan: Plan) -> dict:
    return PLAN_INFO[plan]


class LicenseManager:
    """Persists the active license to ~/.shopping-extractor/license.json."""

    def __init__(self) -> None:
        LICENSE_DIR.mkdir(parents=True, exist_ok=True)

    def load(self) -> License:
        if not LICENSE_PATH.exists():
            return self._default()
        try:
            data = json.loads(LICENSE_PATH.read_text())
            stored = License(
                plan=Plan(data["plan"]),
                expires_at=data["expires_at"],
                key=data["key"],
            )
        except Exception:
            return self._default()
        # Re-verify against the signed key — defends against direct file edits
        verified = parse_key(stored.key)
        if not verified:
            return self._default()
        if verified.plan != stored.plan or verified.expires_at != stored.expires_at:
            return self._default()
        if not verified.is_valid():
            return self._default()
        return verified

    def activate(self, key: str) -> License | None:
        lic = parse_key(key)
        if lic is None or not lic.is_valid():
            return None
        LICENSE_PATH.write_text(json.dumps(asdict(lic), indent=2))
        return lic

    def deactivate(self) -> None:
        if LICENSE_PATH.exists():
            LICENSE_PATH.unlink()

    @staticmethod
    def _default() -> License:
        return License(plan=Plan.FREE, expires_at="2099-12-31", key="FREE")


class UsageTracker:
    """Tracks number of extractions used today (resets at local midnight)."""

    def __init__(self) -> None:
        LICENSE_DIR.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        if not USAGE_PATH.exists():
            return {"date": "", "count": 0}
        try:
            return json.loads(USAGE_PATH.read_text())
        except Exception:
            return {"date": "", "count": 0}

    def _save(self, data: dict) -> None:
        USAGE_PATH.write_text(json.dumps(data))

    def today(self) -> int:
        data = self._load()
        if data.get("date") != date.today().isoformat():
            return 0
        return int(data.get("count", 0))

    def increment(self) -> int:
        today = date.today().isoformat()
        data = self._load()
        if data.get("date") != today:
            data = {"date": today, "count": 0}
        data["count"] = int(data.get("count", 0)) + 1
        self._save(data)
        return data["count"]


def can_extract(plan: Plan, used_today: int) -> tuple[bool, str]:
    info = PLAN_INFO[plan]
    limit = info["daily_limit"]
    if limit is not None and used_today >= limit:
        return False, (
            f"Daily limit reached ({limit}/day on {info['label']} plan). "
            f"Upgrade to Pro for unlimited extractions."
        )
    return True, ""


def clamp_max_products(plan: Plan, requested: int) -> int:
    cap = PLAN_INFO[plan]["max_products"]
    return min(requested, cap)
