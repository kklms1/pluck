"""Playwright 기반 쇼핑몰 페이지 스크래퍼.

페이지를 로드하고, lazy-load 이미지를 강제 트리거하기 위해 끝까지 스크롤한 뒤
제품 카드 영역의 bounding box 좌표로 개별 크롭 이미지를 만든다.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from PIL import Image
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PWTimeout,
    async_playwright,
)

log = logging.getLogger(__name__)


@dataclass
class ProductCard:
    """제품 카드 한 건의 raw 정보 (Vision 분석 전 단계)."""

    index: int
    image_path: str
    product_url: str | None
    raw_html: str
    bbox: tuple[float, float, float, float]  # x, y, w, h
    html_hints: dict[str, str | None] = field(default_factory=dict)


# 다양한 쇼핑몰에서 제품 카드를 찾기 위한 셀렉터 후보군.
# 위에서부터 차례대로 시도하고, 가장 많은 카드를 잡는 셀렉터를 채택한다.
PRODUCT_CARD_SELECTORS = [
    "li.baby-product",                       # Coupang
    "li.search-product",                     # Coupang search
    "div.baby-product",
    "li[class*='product-item']",
    "div[class*='product-item']",
    "li[class*='ProductCard']",
    "div[class*='ProductCard']",
    "li[class*='product-card']",
    "div[class*='product-card']",
    "li[class*='goods']",
    "div[class*='goods']",
    "article[class*='product']",
    "li.product",
    "div.product",
    "[data-product-id]",
]


class PageScraper:
    """Playwright로 페이지를 열어 스크린샷 + 카드 크롭을 만든다."""

    def __init__(
        self,
        output_dir: Path,
        headless: bool = True,
        max_products: int = 20,
        progress_cb: Callable[[str], None] | None = None,
    ):
        self.output_dir = Path(output_dir)
        self.images_dir = self.output_dir / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.max_products = max_products
        self.progress_cb = progress_cb or (lambda msg: log.info(msg))

        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._ctx: BrowserContext | None = None

    async def __aenter__(self) -> "PageScraper":
        self._pw = await async_playwright().start()
        # 일부 anti-bot은 headless-shell의 시그니처를 본다 — 정식 chromium 채널을 우선 시도
        self._browser = await self._pw.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        # 봇 차단을 줄이기 위해 일반적인 브라우저처럼 보이게 설정
        self._ctx = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 900},
            locale="ko-KR",
            extra_http_headers={
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        )
        # navigator.webdriver / plugins / languages 등 자동화 탐지 시그니처 제거
        await self._ctx.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['ko-KR', 'ko', 'en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
            """
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._ctx:
            await self._ctx.close()
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    async def _load_page(self, url: str, retries: int = 3) -> Page:
        last_err: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                assert self._ctx is not None
                page = await self._ctx.new_page()
                self.progress_cb(f"[{attempt}/{retries}] Loading page: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
                # networkidle never fires on some sites — best-effort
                try:
                    await page.wait_for_load_state("networkidle", timeout=15_000)
                except PWTimeout:
                    self.progress_cb("networkidle not reached — continuing anyway")
                return page
            except Exception as e:
                last_err = e
                self.progress_cb(f"Load attempt {attempt} failed: {e!r}")
                await asyncio.sleep(2 * attempt)
        raise RuntimeError(f"Page load failed after 3 retries: {last_err!r}")

    async def _scroll_to_bottom(self, page: Page) -> None:
        """Trigger lazy-load by scrolling until height stabilizes."""
        self.progress_cb("Scrolling to bottom to trigger lazy-loaded images")
        prev_height = 0
        for _ in range(40):  # 최대 40회 스크롤
            curr_height = await page.evaluate("document.body.scrollHeight")
            if curr_height == prev_height:
                break
            prev_height = curr_height
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(0.6)
        # 위로 다시 올라와서 상단도 렌더링 보장
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)

    async def _pick_card_selector(self, page: Page) -> str | None:
        best: tuple[str, int] | None = None
        for sel in PRODUCT_CARD_SELECTORS:
            try:
                count = await page.locator(sel).count()
            except Exception:
                continue
            if count >= 3 and (best is None or count > best[1]):
                best = (sel, count)
        if best:
            self.progress_cb(f"Picked product-card selector: {best[0]} ({best[1]} cards)")
            return best[0]
        self.progress_cb("Could not auto-detect product cards on this page")
        return None

    @staticmethod
    def _resolve_url(href: str | None, base: str) -> str | None:
        if not href:
            return None
        if href.startswith("//"):
            return "https:" + href
        if href.startswith("/"):
            m = re.match(r"^(https?://[^/]+)", base)
            return (m.group(1) if m else "") + href
        return href

    async def _take_full_screenshot(self, page: Page) -> Path:
        path = self.output_dir / "page_full.png"
        # full_page=True 는 페이지 전체를 합성한 결과를 만든다 (뷰포트 좌표와 다름).
        # 카드 크롭은 뷰포트 좌표 기반이므로 두 종류 모두 저장.
        await page.screenshot(path=str(path), full_page=True)
        self.progress_cb(f"Saved full-page screenshot: {path}")
        return path

    async def _crop_cards(
        self,
        page: Page,
        selector: str,
    ) -> list[ProductCard]:
        cards: list[ProductCard] = []
        locator = page.locator(selector)
        total = await locator.count()
        limit = min(total, self.max_products)
        self.progress_cb(f"Found {total} product card(s) — processing top {limit}")

        # full-page 좌표계로 일관되게 크롭하기 위해, 카드별로 스크롤 → 뷰포트 좌표 →
        # PIL로 한 번에 클립하는 대신, 각 element 자체에 element.screenshot()을 사용한다.
        # element.screenshot()은 자동으로 스크롤하고 element만 캡쳐해준다.
        url_base = page.url

        for i in range(limit):
            try:
                el = locator.nth(i)
                await el.scroll_into_view_if_needed(timeout=5_000)
                box = await el.bounding_box()
                if not box or box["width"] < 30 or box["height"] < 30:
                    continue

                img_path = self.images_dir / f"product_{i + 1:03d}.png"
                await el.screenshot(path=str(img_path), timeout=10_000)

                # 너무 크면 Vision API 비용 절약을 위해 다운스케일
                self._maybe_downscale(img_path, max_side=1024)

                href = await el.evaluate(
                    "(node) => {"
                    " const a = node.matches('a') ? node : node.querySelector('a[href]');"
                    " return a ? a.getAttribute('href') : null; }"
                )
                raw_html = await el.evaluate("(n) => n.outerHTML")

                cards.append(
                    ProductCard(
                        index=i + 1,
                        image_path=str(img_path),
                        product_url=self._resolve_url(href, url_base),
                        raw_html=raw_html,
                        bbox=(box["x"], box["y"], box["width"], box["height"]),
                    )
                )
                if (i + 1) % 5 == 0:
                    self.progress_cb(f"  ...{i + 1}/{limit} cropped")
            except Exception as e:
                self.progress_cb(f"  Card {i + 1} crop failed: {e!r} (skipping)")
                continue
        self.progress_cb(f"Cropped {len(cards)} card(s) successfully")
        return cards

    @staticmethod
    def _maybe_downscale(path: Path, max_side: int) -> None:
        try:
            with Image.open(path) as im:
                w, h = im.size
                m = max(w, h)
                if m <= max_side:
                    return
                ratio = max_side / m
                im = im.convert("RGB")
                im = im.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
                im.save(path, format="PNG", optimize=True)
        except Exception as e:
            log.warning("downscale 실패 %s: %r", path, e)

    async def scrape(self, url: str) -> tuple[list[ProductCard], Path, str]:
        """Returns (cards, full_screenshot_path, page_html)."""
        page = await self._load_page(url)
        try:
            await self._scroll_to_bottom(page)
            full_shot = await self._take_full_screenshot(page)
            sel = await self._pick_card_selector(page)
            cards: list[ProductCard] = []
            if sel:
                cards = await self._crop_cards(page, sel)
            html = await page.content()
            return cards, full_shot, html
        finally:
            await page.close()


async def scrape_url(
    url: str,
    output_dir: Path,
    max_products: int = 20,
    headless: bool = True,
    progress_cb: Callable[[str], None] | None = None,
) -> tuple[list[ProductCard], Path, str]:
    async with PageScraper(
        output_dir=output_dir,
        headless=headless,
        max_products=max_products,
        progress_cb=progress_cb,
    ) as s:
        return await s.scrape(url)
