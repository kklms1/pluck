"""Multi-engine vision/OCR analyzer for product card images.

Engines:
  - "local"   : PaddleOCR / EasyOCR / Tesseract (no API key, free, on-device)
  - "claude"  : Anthropic Claude Vision (highest accuracy)
  - "openai"  : GPT-4o / GPT-4o-mini Vision
  - "gemini"  : Google Gemini Vision (free tier available)
  - "ollama"  : Local LLaVA via Ollama (no API key, fully offline)

All engines return a `VisionResult` with name/price/discount_rate (+ optional extra).
The local engine never calls an external API, so the app works out-of-the-box.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

log = logging.getLogger(__name__)

EngineName = Literal["local", "claude", "openai", "gemini", "ollama"]

DEFAULT_MODEL_BY_ENGINE: dict[str, str] = {
    "local": "paddleocr",
    "claude": "claude-sonnet-4-20250514",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.0-flash",
    "ollama": "llava:7b",
}

BASE_SYSTEM = (
    "You are a product information extractor. Analyze the shopping card image "
    "and return a SINGLE JSON object only — no markdown, no commentary. "
    'Schema: {"name": string|null, "price": string|null, "discount_rate": string|null}. '
    "Keep the price exactly as shown (with currency symbol). Use null for missing fields."
)

EXTRA_HINT = (
    ' If the user gives extra instructions, also return matching fields under "extra" '
    "as a flat JSON object using snake_case keys, e.g. "
    '{"name":"...","price":"...","discount_rate":"...","extra":{"size":"L","color":"black"}}. '
    "Use null for any extra field not visible."
)

PRICE_RE = re.compile(
    r"([₩$￥€£]\s?\d+(?:[,.]\d+)*"
    r"|\d{1,3}(?:,\d{3})+(?:\.\d+)?\s?(?:원|won|krw|usd)?"
    r"|\d+\s?(?:원|won|krw))",
    re.IGNORECASE,
)
DISCOUNT_RE = re.compile(r"(\d{1,3}\s?%)")


@dataclass
class VisionResult:
    name: str | None
    price: str | None
    discount_rate: str | None
    extra: dict = field(default_factory=dict)
    raw_response: str | None = None
    error: str | None = None


def _encode_image(path: Path) -> tuple[str, str]:
    data = Path(path).read_bytes()
    suffix = Path(path).suffix.lower().lstrip(".") or "png"
    media_type = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "webp": "image/webp",
    }.get(suffix, "image/png")
    return base64.standard_b64encode(data).decode("ascii"), media_type


def _parse_json_loose(text: str) -> dict | None:
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


# ============================================================
#  Engine: LOCAL (OCR-based, no API key)
# ============================================================
class _LocalOCREngine:
    """OCR-only engine. Tries PaddleOCR → EasyOCR → Tesseract.

    Picks the longest plausible text as `name`, and uses regex to extract
    price/discount from the recognized text. No network calls.
    """

    def __init__(self) -> None:
        self._impl = None
        self._impl_name = None
        self._init_lock = asyncio.Lock()

    async def _ensure(self) -> None:
        if self._impl is not None:
            return
        async with self._init_lock:
            if self._impl is not None:
                return
            # Try PaddleOCR first (best at numbers / Korean)
            try:
                from paddleocr import PaddleOCR  # type: ignore
                self._impl = PaddleOCR(use_angle_cls=False, lang="korean", show_log=False)
                self._impl_name = "paddleocr"
                return
            except Exception as e:
                log.info("PaddleOCR not available: %r", e)
            try:
                import easyocr  # type: ignore
                self._impl = easyocr.Reader(["ko", "en"], gpu=False, verbose=False)
                self._impl_name = "easyocr"
                return
            except Exception as e:
                log.info("EasyOCR not available: %r", e)
            try:
                import pytesseract  # type: ignore
                self._impl = pytesseract
                self._impl_name = "tesseract"
                return
            except Exception as e:
                log.info("Tesseract not available: %r", e)
            self._impl_name = "none"

    async def analyze(self, image_path: Path) -> VisionResult:
        await self._ensure()
        if self._impl_name in (None, "none"):
            return VisionResult(
                None, None, None,
                error="No local OCR backend installed. Install paddleocr / easyocr / pytesseract.",
            )
        loop = asyncio.get_event_loop()
        try:
            lines = await loop.run_in_executor(None, self._read_lines, image_path)
        except Exception as e:
            return VisionResult(None, None, None, error=f"OCR failed: {e!r}")

        text_blob = " ".join(lines)
        # Heuristic: longest line ≥ 5 chars, not pure number/symbol → likely product name
        name = None
        for ln in sorted(lines, key=len, reverse=True):
            stripped = ln.strip()
            if len(stripped) >= 5 and re.search(r"[A-Za-z가-힣]", stripped):
                name = stripped[:200]
                break

        price = None
        m = PRICE_RE.search(text_blob)
        if m:
            price = m.group(1).strip()

        discount = None
        m = DISCOUNT_RE.search(text_blob)
        if m:
            discount = m.group(1).replace(" ", "")

        return VisionResult(
            name=name, price=price, discount_rate=discount,
            raw_response=text_blob,
        )

    def _read_lines(self, image_path: Path) -> list[str]:
        if self._impl_name == "paddleocr":
            res = self._impl.ocr(str(image_path), cls=False)
            lines: list[str] = []
            for page in res or []:
                for item in page or []:
                    try:
                        lines.append(item[1][0])
                    except Exception:
                        continue
            return lines
        if self._impl_name == "easyocr":
            return [t for (_, t, _) in self._impl.readtext(str(image_path))]
        if self._impl_name == "tesseract":
            from PIL import Image
            txt = self._impl.image_to_string(Image.open(image_path), lang="kor+eng")
            return [ln.strip() for ln in txt.splitlines() if ln.strip()]
        return []


# ============================================================
#  Engine: CLAUDE (Anthropic)
# ============================================================
class _ClaudeEngine:
    def __init__(self, api_key: str | None, model: str) -> None:
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=api_key) if api_key else AsyncAnthropic()
        self.model = model

    async def analyze(self, image_path: Path, system: str, user_text: str) -> VisionResult:
        from anthropic import APIError
        try:
            b64, media_type = _encode_image(image_path)
        except Exception as e:
            return VisionResult(None, None, None, error=f"encode failed: {e!r}")
        try:
            msg = await self.client.messages.create(
                model=self.model,
                max_tokens=768,
                system=system,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {
                            "type": "base64", "media_type": media_type, "data": b64,
                        }},
                        {"type": "text", "text": user_text},
                    ],
                }],
            )
        except APIError as e:
            return VisionResult(None, None, None, error=f"Claude API failed: {e!r}")
        except Exception as e:
            return VisionResult(None, None, None, error=f"Claude call failed: {e!r}")
        text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text").strip()
        return _result_from_json(text)


# ============================================================
#  Engine: OPENAI (GPT-4o)
# ============================================================
class _OpenAIEngine:
    def __init__(self, api_key: str | None, model: str) -> None:
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key) if api_key else AsyncOpenAI()
        self.model = model

    async def analyze(self, image_path: Path, system: str, user_text: str) -> VisionResult:
        try:
            b64, media_type = _encode_image(image_path)
        except Exception as e:
            return VisionResult(None, None, None, error=f"encode failed: {e!r}")
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=768,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": [
                        {"type": "text", "text": user_text},
                        {"type": "image_url", "image_url": {
                            "url": f"data:{media_type};base64,{b64}",
                        }},
                    ]},
                ],
            )
        except Exception as e:
            return VisionResult(None, None, None, error=f"OpenAI call failed: {e!r}")
        text = (resp.choices[0].message.content or "").strip()
        return _result_from_json(text)


# ============================================================
#  Engine: GEMINI (Google)
# ============================================================
class _GeminiEngine:
    def __init__(self, api_key: str | None, model: str) -> None:
        import google.generativeai as genai
        if api_key:
            genai.configure(api_key=api_key)
        self._genai = genai
        self.model_name = model

    async def analyze(self, image_path: Path, system: str, user_text: str) -> VisionResult:
        try:
            from PIL import Image
            img = Image.open(image_path)
        except Exception as e:
            return VisionResult(None, None, None, error=f"open image failed: {e!r}")
        try:
            model = self._genai.GenerativeModel(self.model_name, system_instruction=system)
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, lambda: model.generate_content([user_text, img])
            )
            text = (resp.text or "").strip()
        except Exception as e:
            return VisionResult(None, None, None, error=f"Gemini call failed: {e!r}")
        return _result_from_json(text)


# ============================================================
#  Engine: OLLAMA (local LLaVA)
# ============================================================
class _OllamaEngine:
    def __init__(self, model: str, host: str = "http://localhost:11434") -> None:
        self.model = model
        self.host = host.rstrip("/")

    async def analyze(self, image_path: Path, system: str, user_text: str) -> VisionResult:
        import httpx
        try:
            b64, _ = _encode_image(image_path)
        except Exception as e:
            return VisionResult(None, None, None, error=f"encode failed: {e!r}")
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                r = await client.post(
                    f"{self.host}/api/chat",
                    json={
                        "model": self.model,
                        "stream": False,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user_text, "images": [b64]},
                        ],
                    },
                )
                r.raise_for_status()
                data = r.json()
                text = (data.get("message", {}).get("content") or "").strip()
        except Exception as e:
            return VisionResult(
                None, None, None,
                error=f"Ollama call failed (is `ollama serve` running?): {e!r}",
            )
        return _result_from_json(text)


def _result_from_json(text: str) -> VisionResult:
    data = _parse_json_loose(text) or {}
    extra = data.get("extra") or {}
    if not isinstance(extra, dict):
        extra = {"value": str(extra)}
    return VisionResult(
        name=(data.get("name") or None),
        price=(data.get("price") or None),
        discount_rate=(data.get("discount_rate") or None),
        extra=extra,
        raw_response=text,
    )


# ============================================================
#  Public unified analyzer
# ============================================================
class VisionAnalyzer:
    def __init__(
        self,
        engine: EngineName = "local",
        api_key: str | None = None,
        model: str | None = None,
        concurrency: int = 3,
        custom_instructions: str | None = None,
    ):
        self.engine = engine
        self.model = model or DEFAULT_MODEL_BY_ENGINE.get(engine, "")
        self.sem = asyncio.Semaphore(concurrency)
        self.custom_instructions = (custom_instructions or "").strip()

        if engine == "local":
            self._impl = _LocalOCREngine()
        elif engine == "claude":
            self._impl = _ClaudeEngine(api_key, self.model)
        elif engine == "openai":
            self._impl = _OpenAIEngine(api_key, self.model)
        elif engine == "gemini":
            self._impl = _GeminiEngine(api_key, self.model)
        elif engine == "ollama":
            self._impl = _OllamaEngine(self.model)
        else:
            raise ValueError(f"Unknown engine: {engine}")

    @property
    def system_prompt(self) -> str:
        return BASE_SYSTEM + (EXTRA_HINT if self.custom_instructions else "")

    @property
    def user_text(self) -> str:
        if self.custom_instructions:
            return (
                "Extract product info from this image as JSON.\n"
                f"Extra instructions: {self.custom_instructions}"
            )
        return "Extract product info from this image as JSON."

    async def analyze(self, image_path: str | Path) -> VisionResult:
        async with self.sem:
            p = Path(image_path)
            if self.engine == "local":
                return await self._impl.analyze(p)
            return await self._impl.analyze(p, self.system_prompt, self.user_text)

    async def analyze_many(self, image_paths: list[str | Path]) -> list[VisionResult]:
        return await asyncio.gather(*(self.analyze(p) for p in image_paths))
