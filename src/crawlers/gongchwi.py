"""
공취사(gongchwi.com) 채용공고 크롤러
최근 공고난 공기업 리스트 수집
"""

import requests
from bs4 import BeautifulSoup
import time
import logging
from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)

BASE_URL = "https://www.gongchwi.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://www.gongchwi.com",
}


@dataclass
class JobPosting:
    company_name: str
    job_title: str
    deadline: str
    posted_date: str
    hiring_count: Optional[int]
    job_type: str         # 정규직, 계약직, 인턴 등
    region: str
    detail_url: str
    source: str = "공취사"


class GongchwaCrawler:
    def __init__(self, delay: float = 1.2):
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

    def get_recent_postings(self, pages: int = 3) -> list[JobPosting]:
        """최근 채용공고 수집"""
        postings = []
        url = f"{BASE_URL}/recruit/list"

        for page in range(1, pages + 1):
            logger.info(f"공취사 {page}페이지 수집 중...")
            soup = self._get(url, params={"page": page, "type": "public"})
            if not soup:
                break

            items = soup.select(".recruit-item, .job-list-item, li.item")
            if not items:
                # 구조가 다를 수 있으므로 범용 파싱
                items = soup.select("table.board-list tbody tr")

            for item in items:
                posting = self._parse_item(item)
                if posting:
                    postings.append(posting)

        logger.info(f"공취사 총 {len(postings)}건 수집")
        return postings

    def _parse_item(self, item) -> Optional[JobPosting]:
        try:
            cols = item.select("td")
            if len(cols) < 4:
                return None

            company = cols[0].get_text(strip=True)
            title = cols[1].get_text(strip=True)
            link_tag = cols[1].select_one("a") or item.select_one("a")
            detail_url = BASE_URL + link_tag["href"] if link_tag and link_tag.get("href") else ""
            deadline = cols[-1].get_text(strip=True)
            region = cols[2].get_text(strip=True) if len(cols) > 2 else ""
            job_type = cols[3].get_text(strip=True) if len(cols) > 3 else ""

            count_match = re.search(r"(\d+)명", title)
            hiring_count = int(count_match.group(1)) if count_match else None

            return JobPosting(
                company_name=company,
                job_title=title,
                deadline=deadline,
                posted_date=datetime.now().strftime("%Y-%m-%d"),
                hiring_count=hiring_count,
                job_type=job_type,
                region=region,
                detail_url=detail_url,
            )
        except Exception as e:
            logger.debug(f"파싱 실패: {e}")
            return None

    def get_company_names(self, pages: int = 5) -> list[str]:
        """최근 공고난 공기업명만 추출 (알리오 조회용)"""
        postings = self.get_recent_postings(pages=pages)
        seen = set()
        names = []
        for p in postings:
            if p.company_name and p.company_name not in seen:
                seen.add(p.company_name)
                names.append(p.company_name)
        return names

    def collect_all(self, pages: int = 3) -> list[dict]:
        postings = self.get_recent_postings(pages=pages)
        return [asdict(p) for p in postings]
