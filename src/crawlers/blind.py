"""
블라인드 기업 리뷰 수집기
- 복지/수당/기업문화 키워드 추출
- Playwright 기반 (JS 렌더링 필요)
"""

import asyncio
import logging
import re
from dataclasses import dataclass, asdict, field
from typing import Optional
from collections import Counter

logger = logging.getLogger(__name__)

WELFARE_KEYWORDS = [
    "복지포인트", "식대", "교통비", "주택대출", "자녀학자금",
    "의료비", "건강검진", "휴가", "유연근무", "재택", "당직",
    "성과급", "상여금", "퇴직금", "연금", "4대보험",
    "동호회", "도서비", "어린이집", "사택", "기숙사",
]

CULTURE_KEYWORDS = [
    "꼰대", "수평", "야근", "회식", "눈치", "워라밸",
    "승진", "적체", "소통", "경직", "자유", "보수적",
    "평가", "KPI", "성과", "공정",
]


@dataclass
class BlindReview:
    company_name: str
    rating: float              # 별점 1~5
    pros: str                  # 장점
    cons: str                  # 단점
    welfare_mentions: list[str] = field(default_factory=list)
    culture_mentions: list[str] = field(default_factory=list)


@dataclass
class BlindSummary:
    company_name: str
    avg_rating: float
    review_count: int
    top_welfare: list[str]     # 가장 많이 언급된 복지 top5
    top_issues: list[str]      # 가장 많이 언급된 문제 top5
    welfare_score: float       # 복지 언급 빈도 기반 점수 (0~5)
    culture_score: float       # 문화 긍정도 점수 (0~5)


class BlindCrawler:
    """
    블라인드는 로그인이 필요하고 크롤링 방어가 강함.
    Playwright + 실제 계정 사용 또는 공개 데이터만 수집.
    """

    def __init__(self, delay: float = 2.0):
        self.delay = delay

    async def get_reviews(self, company_name: str, max_pages: int = 5) -> list[BlindReview]:
        """블라인드 기업 리뷰 수집 (Playwright 필요)"""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("playwright 미설치: pip install playwright && playwright install chromium")
            return []

        reviews = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })

            search_url = f"https://www.teamblind.com/kr/search/{requests_encode(company_name)}"
            try:
                await page.goto(search_url, timeout=30000)
                await page.wait_for_timeout(2000)

                items = await page.query_selector_all(".review-item, .company-review")
                for item in items[:max_pages * 10]:
                    review = await self._parse_review(item, company_name)
                    if review:
                        reviews.append(review)
            except Exception as e:
                logger.error(f"블라인드 크롤링 실패 {company_name}: {e}")
            finally:
                await browser.close()

        return reviews

    async def _parse_review(self, element, company_name: str) -> Optional[BlindReview]:
        try:
            rating_el = await element.query_selector(".rating, .score")
            rating = float(await rating_el.inner_text()) if rating_el else 0.0

            pros_el = await element.query_selector(".pros, .good")
            pros = await pros_el.inner_text() if pros_el else ""

            cons_el = await element.query_selector(".cons, .bad")
            cons = await cons_el.inner_text() if cons_el else ""

            full_text = f"{pros} {cons}".lower()
            welfare_hits = [kw for kw in WELFARE_KEYWORDS if kw in full_text]
            culture_hits = [kw for kw in CULTURE_KEYWORDS if kw in full_text]

            return BlindReview(
                company_name=company_name,
                rating=rating,
                pros=pros,
                cons=cons,
                welfare_mentions=welfare_hits,
                culture_mentions=culture_hits,
            )
        except Exception:
            return None

    def summarize(self, reviews: list[BlindReview]) -> Optional[BlindSummary]:
        if not reviews:
            return None

        company = reviews[0].company_name
        avg_rating = sum(r.rating for r in reviews) / len(reviews)

        welfare_counter = Counter()
        issue_counter = Counter()
        for r in reviews:
            welfare_counter.update(r.welfare_mentions)
            issue_counter.update(r.culture_mentions)

        welfare_score = min(5.0, len(welfare_counter) * 0.5)
        culture_score = avg_rating

        return BlindSummary(
            company_name=company,
            avg_rating=round(avg_rating, 2),
            review_count=len(reviews),
            top_welfare=[kw for kw, _ in welfare_counter.most_common(5)],
            top_issues=[kw for kw, _ in issue_counter.most_common(5)],
            welfare_score=round(welfare_score, 1),
            culture_score=round(culture_score, 1),
        )

    def collect(self, company_name: str) -> Optional[dict]:
        reviews = asyncio.run(self.get_reviews(company_name))
        summary = self.summarize(reviews)
        if summary:
            return asdict(summary)
        return None


def requests_encode(text: str) -> str:
    import urllib.parse
    return urllib.parse.quote(text)
