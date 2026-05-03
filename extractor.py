"""Pluck: orchestrates scraping + vision/OCR + HTML parsing → results.json/csv."""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

import pandas as pd

from parser import merge, parse_card_html
from scraper import ProductCard, scrape_url
from vision import EngineName, VisionAnalyzer, VisionResult

log = logging.getLogger(__name__)


@dataclass
class Product:
    id: int
    name: str | None
    price: str | None
    discount_rate: str | None
    image_path: str
    product_url: str | None
    extra: dict = field(default_factory=dict)


@dataclass
class ExtractionResult:
    url: str
    products: list[Product]
    full_screenshot: str
    output_dir: str
    custom_instructions: str | None = None
    engine: str = "local"

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "engine": self.engine,
            "full_screenshot": self.full_screenshot,
            "output_dir": self.output_dir,
            "custom_instructions": self.custom_instructions,
            "products": [asdict(p) for p in self.products],
        }


class PluckExtractor:
    def __init__(
        self,
        output_dir: str | Path = "output",
        max_products: int = 20,
        headless: bool = True,
        engine: EngineName = "local",
        api_key: str | None = None,
        model: str | None = None,
        progress_cb: Callable[[str], None] | None = None,
        custom_instructions: str | None = None,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_products = max_products
        self.headless = headless
        self.engine = engine
        self.api_key = api_key
        self.model = model
        self.progress_cb = progress_cb or (lambda msg: log.info(msg))
        self.custom_instructions = (custom_instructions or "").strip() or None

    async def run(self, url: str) -> ExtractionResult:
        self.progress_cb(f"=== Pluck — extracting: {url} ===")
        self.progress_cb(f"AI engine: {self.engine}")
        if self.custom_instructions:
            self.progress_cb(f"Custom instructions: {self.custom_instructions}")

        cards, full_shot, _page_html = await scrape_url(
            url=url,
            output_dir=self.output_dir,
            max_products=self.max_products,
            headless=self.headless,
            progress_cb=self.progress_cb,
        )

        vision_results: list[VisionResult] = []
        if cards:
            self.progress_cb(f"Analyzing {len(cards)} image(s) with engine='{self.engine}'...")
            try:
                analyzer = VisionAnalyzer(
                    engine=self.engine,
                    api_key=self.api_key,
                    model=self.model,
                    custom_instructions=self.custom_instructions,
                )
                vision_results = await analyzer.analyze_many([c.image_path for c in cards])
            except Exception as e:
                self.progress_cb(f"Vision/OCR failed, falling back to HTML only: {e!r}")
                vision_results = [VisionResult(None, None, None, error=str(e)) for _ in cards]
        else:
            vision_results = []

        products: list[Product] = []
        for card, v in zip(cards, vision_results):
            html_data = parse_card_html(card.raw_html)
            vision_data = {"name": v.name, "price": v.price, "discount_rate": v.discount_rate}
            merged = merge(vision_data, html_data)
            extra_clean = {k: val for k, val in (v.extra or {}).items() if val not in (None, "")}
            products.append(
                Product(
                    id=card.index,
                    name=merged["name"],
                    price=merged["price"],
                    discount_rate=merged["discount_rate"],
                    image_path=card.image_path,
                    product_url=card.product_url,
                    extra=extra_clean,
                )
            )

        result = ExtractionResult(
            url=url,
            products=products,
            full_screenshot=str(full_shot),
            output_dir=str(self.output_dir),
            custom_instructions=self.custom_instructions,
            engine=self.engine,
        )
        self._save(result)
        self.progress_cb(f"=== Done: {len(products)} product(s) → {self.output_dir} ===")
        return result

    def _save(self, result: ExtractionResult) -> None:
        json_path = self.output_dir / "results.json"
        json_path.write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.progress_cb(f"Saved JSON: {json_path}")

        csv_path = self.output_dir / "results.csv"
        rows: list[dict] = []
        for p in result.products:
            row = asdict(p)
            extra = row.pop("extra", {}) or {}
            for k, val in extra.items():
                row[f"extra_{k}"] = val
            rows.append(row)
        df = pd.DataFrame(rows)
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        self.progress_cb(f"Saved CSV: {csv_path}")

    def run_sync(self, url: str) -> ExtractionResult:
        return asyncio.run(self.run(url))


# Backwards-compatible alias
ShoppingExtractor = PluckExtractor
