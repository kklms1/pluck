"""
알리오 내부공시 → 보수규정/인사규정/취업규칙 크롤러
URL 예시: https://alio.go.kr/mobile/organ/organDisclosureDtl.do?apbaId=C0247

흐름:
  1. 내부공시 목록 페이지 파싱 → 규정 파일 링크 추출
  2. 보수규정/인사규정 파일 다운로드 (PDF or HWP)
  3. PDF에서 호봉 테이블 추출
  4. 직급×호봉 → 기본급 행렬 반환
"""

import re
import os
import time
import logging
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_URL = "https://alio.go.kr"
DOWNLOAD_DIR = Path("data/regulations")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://alio.go.kr",
}

# 크롤링 대상 규정명 키워드 (우선순위 순)
REGULATION_TARGETS = [
    "보수규정",       # 기본급 호봉표 핵심
    "보수기준",
    "인사규정",       # 직급 체계
    "취업규칙",       # 수당 항목
    "단체협약",       # 노조 교섭 결과 (수당 세부)
    "보수세칙",
]


@dataclass
class RegulationFile:
    name: str           # 규정명
    file_url: str       # 다운로드 URL
    file_type: str      # pdf / hwp / hwpx / docx
    reg_date: str = ""
    local_path: str = ""


@dataclass
class HobongTable:
    """직급별 호봉 기본급 테이블"""
    company_name: str
    grade: str                          # 직급명 (6급, 5급, ...)
    hobong_steps: list[int]             # 호봉 번호 목록 [1, 2, 3, ...]
    base_salaries: list[int]            # 각 호봉 기본급 (만원 단위)
    source_file: str = ""


@dataclass
class ParsedRegulation:
    company_name: str
    apba_id: str
    hobong_tables: list[HobongTable] = field(default_factory=list)
    allowances: dict = field(default_factory=dict)   # 수당명: 금액(만원)
    raw_text_snippet: str = ""


# ─────────────────────────────────────────────────────────────
# 1. 내부공시 규정 목록 수집
# ─────────────────────────────────────────────────────────────

class AlioRegulationCrawler:
    def __init__(self, delay: float = 1.5):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.delay = delay
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    def _get(self, url: str, params: dict = None) -> Optional[BeautifulSoup]:
        try:
            resp = self.session.get(url, params=params, timeout=20)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            time.sleep(self.delay)
            return BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            logger.error(f"GET 실패 {url}: {e}")
            return None

    def get_regulation_list(self, apba_id: str) -> list[RegulationFile]:
        """내부공시 규정 파일 목록 수집"""
        # 모바일/PC 버전 모두 시도
        urls_to_try = [
            f"{BASE_URL}/mobile/organ/organDisclosureDtl.do?apbaId={apba_id}",
            f"{BASE_URL}/alio/site/main/publicinstitutions/organInternalRegList.do?apbaId={apba_id}",
            f"{BASE_URL}/alio/site/main/publicinstitutions/internalRuleList.do?instCode={apba_id}",
        ]

        for url in urls_to_try:
            soup = self._get(url)
            if not soup:
                continue

            files = self._parse_regulation_links(soup, url)
            if files:
                logger.info(f"규정 목록 {len(files)}건 (URL: {url})")
                return files

        logger.warning(f"규정 목록 수집 실패: apbaId={apba_id}")
        return []

    def _parse_regulation_links(self, soup: BeautifulSoup, base_url: str) -> list[RegulationFile]:
        files = []

        # 패턴 1: <a href="..."> 텍스트에 파일 다운로드 링크
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            text = a.get_text(strip=True)

            if not any(kw in text for kw in REGULATION_TARGETS + ["규정", "규칙", "협약"]):
                if not any(ext in href.lower() for ext in [".pdf", ".hwp", ".hwpx", ".docx"]):
                    continue

            file_type = self._detect_filetype(href, text)
            if not file_type:
                continue

            full_url = href if href.startswith("http") else BASE_URL + href
            files.append(RegulationFile(
                name=text or "unnamed",
                file_url=full_url,
                file_type=file_type,
            ))

        # 패턴 2: onclick="fnFileDown('fileId')" 형태
        for tag in soup.select("[onclick*='fileDown'], [onclick*='download'], [onclick*='File']"):
            onclick = tag.get("onclick", "")
            text = tag.get_text(strip=True)

            # fileId 추출
            match = re.search(r"['\"]([A-Za-z0-9_\-]+\.(?:pdf|hwp|hwpx|docx))['\"]", onclick, re.I)
            if not match:
                # fileId 숫자 패턴
                match = re.search(r"fnFileDown\(['\"]?(\w+)['\"]?\)", onclick)

            if match:
                file_id = match.group(1)
                dl_url = f"{BASE_URL}/alio/file/download.do?fileId={file_id}"
                file_type = self._detect_filetype(file_id, text)
                files.append(RegulationFile(
                    name=text,
                    file_url=dl_url,
                    file_type=file_type or "pdf",
                ))

        # 패턴 3: <table> 내 규정 목록 (날짜, 규정명, 다운로드 버튼)
        for row in soup.select("table tr"):
            cols = row.select("td")
            if len(cols) < 2:
                continue
            reg_name = cols[0].get_text(strip=True) if cols else ""
            if not any(kw in reg_name for kw in REGULATION_TARGETS + ["규정", "규칙", "협약"]):
                continue

            link = row.select_one("a[href], button[onclick]")
            if not link:
                continue

            href = link.get("href", "") or ""
            onclick = link.get("onclick", "") or ""
            url_candidate = href or self._extract_url_from_onclick(onclick)
            if not url_candidate:
                continue

            full_url = url_candidate if url_candidate.startswith("http") else BASE_URL + url_candidate
            files.append(RegulationFile(
                name=reg_name,
                file_url=full_url,
                file_type=self._detect_filetype(url_candidate, reg_name) or "pdf",
                reg_date=cols[1].get_text(strip=True) if len(cols) > 1 else "",
            ))

        # 중복 제거
        seen = set()
        unique = []
        for f in files:
            key = f.file_url
            if key not in seen:
                seen.add(key)
                unique.append(f)
        return unique

    def _detect_filetype(self, url_or_name: str, text: str = "") -> str:
        combined = (url_or_name + text).lower()
        for ext in ["hwpx", "hwp", "pdf", "docx", "xlsx"]:
            if ext in combined:
                return ext
        return ""

    def _extract_url_from_onclick(self, onclick: str) -> str:
        match = re.search(r"['\"](/[^'\"]+)['\"]", onclick)
        return match.group(1) if match else ""

    def download_file(self, reg: RegulationFile, apba_id: str) -> Optional[Path]:
        """규정 파일 다운로드"""
        safe_name = re.sub(r"[^\w가-힣]", "_", reg.name)
        filename = f"{apba_id}_{safe_name}.{reg.file_type}"
        local_path = DOWNLOAD_DIR / filename

        if local_path.exists():
            logger.info(f"  이미 다운로드됨: {local_path}")
            reg.local_path = str(local_path)
            return local_path

        try:
            resp = self.session.get(reg.file_url, timeout=30, stream=True)
            resp.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            reg.local_path = str(local_path)
            logger.info(f"  다운로드: {local_path} ({local_path.stat().st_size:,} bytes)")
            time.sleep(self.delay)
            return local_path
        except Exception as e:
            logger.error(f"  다운로드 실패 {reg.file_url}: {e}")
            return None

    def collect(self, company_name: str, apba_id: str) -> list[RegulationFile]:
        logger.info(f"[{company_name}] 내부규정 수집 시작 (apbaId={apba_id})")
        all_files = self.get_regulation_list(apba_id)

        # 우선순위 정렬: 보수규정 > 인사규정 > 취업규칙 순
        def priority(f: RegulationFile) -> int:
            for i, kw in enumerate(REGULATION_TARGETS):
                if kw in f.name:
                    return i
            return 99

        all_files.sort(key=priority)
        logger.info(f"  발견된 규정: {[f.name for f in all_files]}")

        # 핵심 규정만 다운로드
        downloaded = []
        for f in all_files:
            if any(kw in f.name for kw in REGULATION_TARGETS):
                path = self.download_file(f, apba_id)
                if path:
                    downloaded.append(f)

        return downloaded
