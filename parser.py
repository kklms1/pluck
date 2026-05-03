"""BeautifulSoup으로 카드 HTML에서 제품명/가격/할인율을 보조 추출.

Vision 결과와 머지하여 빠진 필드를 채워주는 역할이라, 실패해도 raise 하지 않는다.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

NAME_SELECTORS = [
    ".name",
    ".product-name",
    ".prod-name",
    ".title",
    ".product-title",
    "[class*='ProductName']",
    "[class*='product-name']",
    "[class*='product_name']",
    "[class*='goods-name']",
    "[class*='title']",
    "h2",
    "h3",
    "h4",
]

PRICE_SELECTORS = [
    ".price",
    ".price-value",
    ".sale-price",
    ".prod-price",
    "[class*='Price']",
    "[class*='price']",
    "strong[class*='price']",
    "em[class*='price']",
    "span[class*='price']",
]

DISCOUNT_SELECTORS = [
    ".discount-rate",
    ".sale-rate",
    ".discount",
    "[class*='discount']",
    "[class*='sale-rate']",
    "[class*='Discount']",
]

# 1) 통화기호 + 숫자 (£51.77, $19.99) 또는 2) 숫자 + 천단위 콤마 + (원) 등
PRICE_RE = re.compile(
    r"([₩$￥€£]\s?\d+(?:[,.]\d+)*"               # £51.77 / $19.99 / ₩12,900
    r"|\d{1,3}(?:,\d{3})+(?:\.\d+)?\s?(?:원|won|krw)?"  # 12,900원 / 1,234,567
    r"|\d+\s?(?:원|won|krw))",                     # 9900원
    re.IGNORECASE,
)
DISCOUNT_RE = re.compile(r"(\d{1,3}\s?%)")


def _first_text(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    for sel in selectors:
        try:
            el = soup.select_one(sel)
        except Exception:
            continue
        if el and (txt := el.get_text(" ", strip=True)):
            return txt
    return None


def _regex_first(soup: BeautifulSoup, pattern: re.Pattern[str]) -> str | None:
    text = soup.get_text(" ", strip=True)
    m = pattern.search(text)
    return m.group(1).strip() if m else None


def parse_card_html(html: str) -> dict:
    """Returns {'name', 'price', 'discount_rate'} (값 없으면 None)."""
    if not html:
        return {"name": None, "price": None, "discount_rate": None}
    soup = BeautifulSoup(html, "lxml")

    name = _first_text(soup, NAME_SELECTORS)
    if name:
        # 너무 긴 노이즈는 잘라낸다 (2줄 이상 안내 문구 등)
        name = re.sub(r"\s+", " ", name)[:200]

    price = _first_text(soup, PRICE_SELECTORS)
    if price:
        # "12,900원 11,200원" 같이 두 개가 같이 잡히면 가장 그럴듯한 것 하나만
        m = PRICE_RE.search(price)
        if m:
            price = m.group(1).strip()
    if not price:
        price = _regex_first(soup, PRICE_RE)

    discount = _first_text(soup, DISCOUNT_SELECTORS)
    if discount:
        m = DISCOUNT_RE.search(discount)
        if m:
            discount = m.group(1).replace(" ", "")
    if not discount:
        discount = _regex_first(soup, DISCOUNT_RE)
        if discount:
            discount = discount.replace(" ", "")

    return {"name": name, "price": price, "discount_rate": discount}


def merge(vision: dict, html: dict) -> dict:
    """Vision 우선, 비어있는 필드만 HTML로 채운다."""
    out = {}
    for k in ("name", "price", "discount_rate"):
        v = vision.get(k)
        if not v:
            v = html.get(k)
        out[k] = v
    return out
