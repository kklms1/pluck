"""
알리오(alio.go.kr) 공공기관 경영정보 크롤러
- 기관별 연봉, 직급, 직원 현황 수집
"""

import requests
from bs4 import BeautifulSoup
import time
import logging
from dataclasses import dataclass, asdict
from typing import Optional
import re

logger = logging.getLogger(__name__)

BASE_URL = "https://www.alio.go.kr"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://www.alio.go.kr",
}


@dataclass
class SalaryRecord:
    company_name: str
    year: int
    avg_salary_10k: int        # 평균연봉 (만원)
    avg_tenure_years: float    # 평균근속연수
    total_employees: int       # 전체 직원수
    new_hire_salary_10k: Optional[int] = None   # 신입 초봉 (만원)
    source_url: str = ""


@dataclass
class GradeRecord:
    company_name: str
    year: int
    grade_name: str            # 직급명 (예: 1급, 2급, 부장, 차장)
    grade_order: int           # 직급 순서 (1이 최고)
    avg_salary_10k: Optional[int] = None
    avg_years_in_grade: Optional[float] = None


class AllioCrawler:
    def __init__(self, delay: float = 1.5):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.delay = delay

    def _get(self, url: str, params: dict = None) -> Optional[BeautifulSoup]:
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            time.sleep(self.delay)
            return BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            logger.error(f"GET 실패 {url}: {e}")
            return None

    def search_company(self, company_name: str) -> Optional[str]:
        """기관명으로 검색해 알리오 기관코드 반환"""
        url = f"{BASE_URL}/alio/site/main/publicinstitutions/publicInstSearch.do"
        soup = self._get(url, params={"searchKeyword": company_name})
        if not soup:
            return None

        rows = soup.select("table.board-list tbody tr")
        for row in rows:
            cols = row.select("td")
            if len(cols) >= 2:
                name_cell = cols[1].get_text(strip=True)
                if company_name in name_cell:
                    link = row.select_one("a")
                    if link and link.get("href"):
                        href = link["href"]
                        match = re.search(r"instCode=(\w+)", href)
                        if match:
                            return match.group(1)
        return None

    def get_salary_info(self, inst_code: str, company_name: str) -> list[SalaryRecord]:
        """기관코드로 연봉 정보 수집"""
        url = f"{BASE_URL}/alio/site/main/publicinstitutions/employInfo.do"
        soup = self._get(url, params={"instCode": inst_code})
        if not soup:
            return []

        records = []
        tables = soup.select("table.board-list")
        for table in tables:
            rows = table.select("tbody tr")
            for row in rows:
                cols = [td.get_text(strip=True) for td in row.select("td")]
                if len(cols) < 4:
                    continue
                try:
                    year = int(re.sub(r"[^\d]", "", cols[0]))
                    avg_salary = int(re.sub(r"[^\d]", "", cols[1])) if cols[1] else 0
                    tenure = float(re.sub(r"[^\d.]", "", cols[2])) if cols[2] else 0.0
                    employees = int(re.sub(r"[^\d]", "", cols[3])) if cols[3] else 0

                    records.append(SalaryRecord(
                        company_name=company_name,
                        year=year,
                        avg_salary_10k=avg_salary,
                        avg_tenure_years=tenure,
                        total_employees=employees,
                        source_url=url,
                    ))
                except (ValueError, IndexError):
                    continue

        return records

    def get_grade_info(self, inst_code: str, company_name: str) -> list[GradeRecord]:
        """직급별 현황 수집"""
        url = f"{BASE_URL}/alio/site/main/publicinstitutions/gradeInfo.do"
        soup = self._get(url, params={"instCode": inst_code})
        if not soup:
            return []

        records = []
        tables = soup.select("table.board-list")
        for table in tables:
            headers = [th.get_text(strip=True) for th in table.select("thead th")]
            rows = table.select("tbody tr")
            for row in rows:
                cols = [td.get_text(strip=True) for td in row.select("td")]
                if not cols:
                    continue
                for i, (header, value) in enumerate(zip(headers, cols)):
                    if not value or value == "-":
                        continue
                    try:
                        year = int(re.sub(r"[^\d]", "", cols[0])) if cols else 0
                        records.append(GradeRecord(
                            company_name=company_name,
                            year=year,
                            grade_name=header,
                            grade_order=i,
                        ))
                    except (ValueError, IndexError):
                        break

        return records

    def collect(self, company_name: str) -> dict:
        """기업명 하나로 모든 데이터 수집"""
        logger.info(f"수집 시작: {company_name}")

        inst_code = self.search_company(company_name)
        if not inst_code:
            logger.warning(f"기관코드 찾기 실패: {company_name}")
            return {"company": company_name, "salary": [], "grades": []}

        salary = self.get_salary_info(inst_code, company_name)
        grades = self.get_grade_info(inst_code, company_name)

        logger.info(f"{company_name}: 연봉 {len(salary)}건, 직급 {len(grades)}건")
        return {
            "company": company_name,
            "inst_code": inst_code,
            "salary": [asdict(r) for r in salary],
            "grades": [asdict(r) for r in grades],
        }
