"""
알리오 Playwright 크롤러 (로그인 없이 stealth 모드)
- 봇 탐지 우회 (playwright-stealth)
- 내부공시 규정 파일 다운로드
- 복리후생비 / 교육훈련비 / 직원현황 등 공시 데이터 수집

실행 전:
  pip install playwright playwright-stealth
  playwright install chromium
"""

import asyncio
import json
import logging
import re
import time
import random
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)

BASE = "https://alio.go.kr"
DOWNLOAD_DIR = Path("data/regulations")
DATA_DIR = Path("data")

# 알리오 공시 URL 맵 (instCode 또는 apbaId로 기관 구분)
DISCLOSURE = {
    # instCode 기반
    "직원현황":      "/alio/site/main/publicinstitutions/employInfo.do",
    "1인당평균보수":  "/alio/site/main/publicinstitutions/averageSalaryInfo.do",
    "복리후생비":    "/alio/site/main/publicinstitutions/welfareExpenseInfo.do",
    "교육훈련비":    "/alio/site/main/publicinstitutions/educationExpenseInfo.do",
    "노동조합":      "/alio/site/main/publicinstitutions/laborUnionInfo.do",
    "신규채용":      "/alio/site/main/publicinstitutions/newHireInfo.do",
    "임원보수":      "/alio/site/main/publicinstitutions/officerSalaryInfo.do",
    # apbaId 기반 (내부공시)
    "내부공시목록":   "/mobile/organ/organDisclosureDtl.do",
}

# 크롤링 대상 규정 우선순위
REGULATION_TARGETS = ["보수규정", "취업규칙", "인사규정", "단체협약", "보수세칙", "복무규정"]


@dataclass
class WelfareData:
    company_name: str
    year: int
    total_welfare_10k: float        # 1인당 복리후생비 총액
    meal_10k: float = 0             # 식대
    transport_10k: float = 0        # 교통비
    health_checkup_10k: float = 0   # 건강검진
    childcare_10k: float = 0        # 보육/학자금
    housing_10k: float = 0         # 주택 관련
    recreation_10k: float = 0      # 문화/여가
    other_10k: float = 0           # 기타


@dataclass
class TrainingData:
    company_name: str
    year: int
    total_training_10k: float          # 교육훈련비 총액
    per_person_10k: float = 0          # 1인당 교육훈련비
    overseas_count: int = 0            # 해외연수 인원
    overseas_expense_10k: float = 0    # 해외연수 비용
    language_training: bool = False    # 어학연수 여부
    mba_support: bool = False          # MBA/학위과정 지원 여부


@dataclass
class LeaveData:
    company_name: str
    annual_leave_days: int = 15        # 연차 일수 (법정 기준)
    summer_leave_days: int = 0         # 여름휴가 별도
    special_leave_days: int = 0        # 경조 등 특별휴가
    sick_leave_days: int = 60          # 병가 일수
    parental_leave_months: int = 12    # 육아휴직 기간
    parental_usage_rate_pct: float = 0 # 육아휴직 사용률
    flexible_work: bool = False        # 유연근무제
    remote_work: bool = False          # 재택근무
    source: str = ""


@dataclass
class CompanyBenefit:
    company_name: str
    welfare: Optional[WelfareData] = None
    training: Optional[TrainingData] = None
    leave: Optional[LeaveData] = None
    union_rate_pct: float = 0         # 노조 가입률
    union_name: str = ""
    notes: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────

async def crawl_company(
    company_name: str,
    inst_code: str,
    apba_id: str,
    headless: bool = True,
    download_regulations: bool = True,
) -> dict:
    """
    메인 크롤링 진입점
    inst_code: 알리오 경영공시 기관코드 (예: A0009)
    apba_id:   내부공시 기관코드 (예: C0247)
    """
    try:
        from playwright.async_api import async_playwright
        from playwright_stealth import stealth_async
    except ImportError:
        raise ImportError(
            "실행 전: pip install playwright playwright-stealth && playwright install chromium"
        )

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    result = {"company": company_name, "inst_code": inst_code, "apba_id": apba_id}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--lang=ko-KR",
            ],
        )

        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            viewport={"width": 1280, "height": 900},
            java_script_enabled=True,
        )

        page = await ctx.new_page()
        await stealth_async(page)

        # 메인 페이지 초기 방문 (쿠키/세션 세팅)
        logger.info(f"[{company_name}] 알리오 메인 접속...")
        await page.goto(BASE, wait_until="domcontentloaded", timeout=30000)
        await _human_delay(1.5, 2.5)

        # 공시 데이터 수집
        logger.info("  공시 데이터 수집 시작...")
        disclosures = await _collect_disclosures(page, inst_code, company_name)
        result["disclosures"] = disclosures

        # 내부공시 규정 파일 다운로드
        if download_regulations and apba_id:
            logger.info("  내부규정 파일 수집...")
            reg_files = await _collect_regulations(page, ctx, apba_id, company_name)
            result["regulation_files"] = reg_files

        await browser.close()

    # JSON 저장
    out = DATA_DIR / f"{company_name}_crawled.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"  저장: {out}")
    return result


async def _collect_disclosures(page, inst_code: str, company_name: str) -> dict:
    """공시 페이지별 테이블 데이터 수집"""
    result = {}

    categories = {
        "1인당평균보수": DISCLOSURE["1인당평균보수"],
        "복리후생비":    DISCLOSURE["복리후생비"],
        "직원현황":      DISCLOSURE["직원현황"],
        "교육훈련비":    DISCLOSURE["교육훈련비"],
        "노동조합":      DISCLOSURE["노동조합"],
        "신규채용":      DISCLOSURE["신규채용"],
    }

    for cat, path in categories.items():
        url = f"{BASE}{path}?instCode={inst_code}"
        logger.info(f"    [{cat}] {url}")

        try:
            await page.goto(url, wait_until="networkidle", timeout=20000)
            await _human_delay(1.0, 2.0)

            tables = await _extract_all_tables(page)
            result[cat] = {"url": url, "tables": tables}
            logger.info(f"    → 테이블 {len(tables)}개")

        except Exception as e:
            logger.error(f"    [{cat}] 실패: {e}")
            result[cat] = {"url": url, "error": str(e), "tables": []}

    return result


async def _collect_regulations(page, ctx, apba_id: str, company_name: str) -> list[dict]:
    """내부공시 규정 목록 수집 및 파일 다운로드"""
    url = f"{BASE}{DISCLOSURE['내부공시목록']}?apbaId={apba_id}"

    try:
        await page.goto(url, wait_until="networkidle", timeout=25000)
        await _human_delay(2.0, 3.0)
        html = await page.content()
    except Exception as e:
        logger.error(f"  내부공시 목록 접근 실패: {e}")
        return []

    files = _parse_regulation_links_from_html(html)
    logger.info(f"  발견된 규정: {[f['name'] for f in files]}")

    downloaded = []
    for f in files:
        if not any(kw in f["name"] for kw in REGULATION_TARGETS):
            continue

        local_path = await _download_file_playwright(ctx, f["url"], company_name, f["name"])
        if local_path:
            f["local_path"] = local_path
            downloaded.append(f)

    return downloaded


def _parse_regulation_links_from_html(html: str) -> list[dict]:
    """HTML에서 규정 파일 링크 추출"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    files = []
    seen = set()

    # 패턴 1: href로 직접 파일 링크
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if not href or href == "#":
            continue
        ext = _detect_ext(href + text)
        if not ext:
            continue
        full_url = href if href.startswith("http") else BASE + href
        if full_url not in seen:
            seen.add(full_url)
            files.append({"name": text or "unnamed", "url": full_url, "ext": ext})

    # 패턴 2: 테이블 행 구조 (규정명 | 날짜 | 다운로드)
    for row in soup.select("table tr"):
        cols = row.select("td")
        if len(cols) < 2:
            continue
        name = cols[0].get_text(strip=True)
        if not name:
            continue
        link = row.select_one("a[href]")
        if not link:
            continue
        href = link.get("href", "")
        ext = _detect_ext(href + name)
        if not ext:
            ext = "pdf"  # 기본값
        full_url = href if href.startswith("http") else BASE + href
        if full_url not in seen:
            seen.add(full_url)
            files.append({"name": name, "url": full_url, "ext": ext})

    # 패턴 3: onclick에서 파일 ID 추출
    for tag in soup.select("[onclick]"):
        onclick = tag.get("onclick", "")
        text = tag.get_text(strip=True)

        # fnFileDown('FILEID') 패턴
        m = re.search(r"fnFileDown[^(]*\(['\"]?([^'\"(),\s]+)['\"]?\)", onclick)
        if m:
            file_id = m.group(1)
            url = f"{BASE}/alio/cmm/file/fileDown.do?atchFileId={file_id}"
            ext = _detect_ext(onclick + text) or "hwp"
            if url not in seen:
                seen.add(url)
                files.append({"name": text or file_id, "url": url, "ext": ext})

    return files


async def _download_file_playwright(ctx, url: str, company_name: str, reg_name: str) -> Optional[str]:
    """Playwright로 파일 다운로드 (리다이렉트/JS 핸들링)"""
    safe_name = re.sub(r"[^\w가-힣]", "_", reg_name)[:40]
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    try:
        page = await ctx.new_page()
        dl_path = None

        async with page.expect_download(timeout=30000) as dl_info:
            await page.goto(url, timeout=20000)

        download = await dl_info.value
        ext = Path(download.suggested_filename).suffix or ".pdf"
        local_path = DOWNLOAD_DIR / f"{company_name}_{safe_name}{ext}"
        await download.save_as(str(local_path))
        dl_path = str(local_path)
        logger.info(f"    다운로드: {local_path}")

    except Exception as e:
        logger.warning(f"    다운로드 실패 {url}: {e}")
        dl_path = None
    finally:
        await page.close()

    return dl_path


async def _extract_all_tables(page) -> list[list[list[str]]]:
    """페이지의 모든 테이블 추출"""
    tables_data = await page.evaluate("""() => {
        const tables = document.querySelectorAll('table');
        return Array.from(tables).map(table => {
            const rows = table.querySelectorAll('tr');
            return Array.from(rows).map(row => {
                const cells = row.querySelectorAll('th, td');
                return Array.from(cells).map(c => c.innerText.trim());
            }).filter(row => row.some(c => c));
        }).filter(t => t.length > 0);
    }""")
    return tables_data


async def _human_delay(min_s: float = 0.8, max_s: float = 2.0):
    await asyncio.sleep(random.uniform(min_s, max_s))


def _detect_ext(s: str) -> str:
    s = s.lower()
    for ext in ["hwpx", "hwp", "pdf", "docx", "xlsx"]:
        if ext in s:
            return ext
    return ""


# ─────────────────────────────────────────────────────────────
# 동기 래퍼
# ─────────────────────────────────────────────────────────────

def run(company_name: str, inst_code: str, apba_id: str,
        headless: bool = True, download_regulations: bool = True) -> dict:
    return asyncio.run(crawl_company(
        company_name, inst_code, apba_id, headless, download_regulations
    ))
