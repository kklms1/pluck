"""
블라인드 기업 리뷰 수집기 (Playwright 기반)
- 기업 종합 평점 + 항목별 평점
- 리뷰 텍스트 키워드 추출
- 기업 평점 화면 스크린샷 (영상 삽입용)
"""

import asyncio
import logging
import re
import urllib.parse
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
from collections import Counter

logger = logging.getLogger(__name__)

SCREENSHOT_DIR = Path("output/screenshots")

WELFARE_KEYWORDS = [
    "복지포인트", "식대", "교통비", "주택대출", "자녀학자금",
    "의료비", "건강검진", "휴가", "유연근무", "재택", "당직",
    "성과급", "상여금", "퇴직금", "연금", "4대보험",
    "동호회", "도서비", "어린이집", "사택", "기숙사",
]

CULTURE_KEYWORDS = [
    "꼰대", "수평", "야근", "회식", "눈치", "워라밸",
    "승진적체", "소통", "경직", "자유", "보수적", "공정",
]


@dataclass
class BlindRating:
    company_name: str
    overall: float = 0.0           # 종합 평점 (5점 만점)
    salary_benefit: float = 0.0    # 급여·복지
    work_life: float = 0.0         # 워라밸
    culture: float = 0.0           # 사내문화
    management: float = 0.0        # 경영진
    growth: float = 0.0            # 성장 가능성
    recommend_pct: float = 0.0     # 친구 추천 비율
    ceo_approval_pct: float = 0.0  # CEO 지지율
    review_count: int = 0
    top_welfare_keywords: list[str] = field(default_factory=list)
    top_culture_issues: list[str] = field(default_factory=list)
    screenshot_path: str = ""      # 평점 화면 스크린샷 경로


async def get_blind_rating(
    company_name: str,
    headless: bool = True,
    take_screenshot: bool = True,
) -> Optional[BlindRating]:
    """블라인드 기업 평점 + 키워드 수집"""
    try:
        from playwright.async_api import async_playwright
        from playwright_stealth import stealth_async
    except ImportError:
        logger.error("pip install playwright playwright-stealth && playwright install chromium")
        return None

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    rating = BlindRating(company_name=company_name)
    encoded = urllib.parse.quote(company_name)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
            ),
            locale="ko-KR",
            viewport={"width": 1280, "height": 900},
        )
        page = await ctx.new_page()
        await stealth_async(page)

        # 블라인드 기업 검색
        search_url = f"https://www.teamblind.com/kr/search/{encoded}"
        try:
            await page.goto(search_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)

            # 첫 번째 기업 결과 클릭
            company_link = await page.query_selector(
                "a[href*='/company/'], .company-name a, .search-result a"
            )
            if company_link:
                await company_link.click()
                await asyncio.sleep(2)
            else:
                # 직접 URL 시도
                direct_url = f"https://www.teamblind.com/kr/company/{encoded}/reviews"
                await page.goto(direct_url, wait_until="networkidle", timeout=20000)
                await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"블라인드 접속 실패: {e}")
            await browser.close()
            return None

        # 평점 파싱
        rating = await _parse_blind_page(page, rating)

        # 스크린샷 (평점 섹션만 캡처)
        if take_screenshot:
            rating.screenshot_path = await _capture_rating_screenshot(
                page, company_name
            )

        # 리뷰 텍스트 수집
        rating = await _collect_review_keywords(page, rating)

        await browser.close()

    logger.info(
        f"블라인드 [{company_name}] 평점:{rating.overall} "
        f"리뷰:{rating.review_count}개"
    )
    return rating


async def _parse_blind_page(page, rating: BlindRating) -> BlindRating:
    """블라인드 페이지에서 평점 추출"""
    try:
        content = await page.content()

        # 종합 평점
        overall_el = await page.query_selector(
            ".overall-score, .company-score, [class*='overall'] [class*='score'], "
            "[class*='rating-score'], .score-number"
        )
        if overall_el:
            text = await overall_el.inner_text()
            m = re.search(r"[\d.]+", text)
            if m:
                rating.overall = float(m.group())

        # 항목별 평점 (여러 셀렉터 시도)
        score_items = await page.query_selector_all(
            "[class*='category-score'], [class*='sub-score'], "
            ".rating-item, [class*='breakdown']"
        )
        labels = ["급여·복지", "워라밸", "사내문화", "경영진", "성장 가능성"]
        score_fields = ["salary_benefit", "work_life", "culture", "management", "growth"]

        for i, (label, field_name) in enumerate(zip(labels, score_fields)):
            if i < len(score_items):
                text = await score_items[i].inner_text()
                m = re.search(r"[\d.]+", text)
                if m:
                    setattr(rating, field_name, float(m.group()))

        # 추천/CEO 지지율
        recommend_el = await page.query_selector(
            "[class*='recommend'], [class*='positive']"
        )
        if recommend_el:
            text = await recommend_el.inner_text()
            m = re.search(r"(\d+)\s*%", text)
            if m:
                rating.recommend_pct = float(m.group(1))

        # 리뷰 수
        count_el = await page.query_selector(
            "[class*='review-count'], [class*='total-review']"
        )
        if count_el:
            text = await count_el.inner_text()
            m = re.search(r"[\d,]+", text)
            if m:
                rating.review_count = int(m.group().replace(",", ""))

        # 텍스트 기반 폴백 (JS 렌더링 실패 시)
        if rating.overall == 0:
            text_all = await page.evaluate("() => document.body.innerText")
            m = re.search(r"종합\s*평점[^\d]*([\d.]+)", text_all)
            if m:
                rating.overall = float(m.group(1))

    except Exception as e:
        logger.warning(f"평점 파싱 실패: {e}")

    return rating


async def _capture_rating_screenshot(page, company_name: str) -> str:
    """평점 섹션 스크린샷 캡처"""
    screenshot_path = str(
        SCREENSHOT_DIR / f"{company_name}_blind_rating.png"
    )
    try:
        # 평점 영역만 클리핑
        rating_el = await page.query_selector(
            "[class*='company-rating'], [class*='rating-section'], "
            "[class*='score-section'], .company-overview"
        )
        if rating_el:
            await rating_el.screenshot(path=screenshot_path)
        else:
            # 전체 페이지 스크린샷 폴백
            await page.screenshot(path=screenshot_path, full_page=False)

        logger.info(f"스크린샷 저장: {screenshot_path}")
    except Exception as e:
        logger.warning(f"스크린샷 실패: {e}")
        screenshot_path = ""

    return screenshot_path


async def _collect_review_keywords(page, rating: BlindRating) -> BlindRating:
    """리뷰 텍스트에서 키워드 추출"""
    try:
        review_els = await page.query_selector_all(
            "[class*='review-content'], [class*='review-text'], "
            "[class*='pros'], [class*='cons']"
        )
        full_text = ""
        for el in review_els[:50]:
            full_text += await el.inner_text() + " "

        welfare_c = Counter(kw for kw in WELFARE_KEYWORDS if kw in full_text)
        culture_c = Counter(kw for kw in CULTURE_KEYWORDS if kw in full_text)

        rating.top_welfare_keywords = [k for k, _ in welfare_c.most_common(5)]
        rating.top_culture_issues = [k for k, _ in culture_c.most_common(5)]
    except Exception as e:
        logger.debug(f"키워드 추출 실패: {e}")

    return rating


# ── 동기 래퍼 ──────────────────────────────────────────────────

def get_rating(
    company_name: str,
    headless: bool = True,
    take_screenshot: bool = True,
) -> Optional[dict]:
    result = asyncio.run(
        get_blind_rating(company_name, headless, take_screenshot)
    )
    return asdict(result) if result else None


def format_blind_summary(rating: BlindRating) -> str:
    """블라인드 평점 영상 자막용 텍스트"""
    stars = "★" * round(rating.overall) + "☆" * (5 - round(rating.overall))
    lines = [
        f"블라인드 종합 {rating.overall:.1f}점  {stars}  ({rating.review_count:,}개 리뷰)",
        f"급여·복지 {rating.salary_benefit:.1f}  |  워라밸 {rating.work_life:.1f}  |  "
        f"사내문화 {rating.culture:.1f}  |  성장 {rating.growth:.1f}",
    ]
    if rating.top_welfare_keywords:
        lines.append(f"자주 언급: {' / '.join(rating.top_welfare_keywords)}")
    return "\n".join(lines)
