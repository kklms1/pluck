"""
공공기관 평가위원 풀 분석
- 해당 기업 임직원의 외부 평가위원 활동률 조사
- 성장 가능성 지표로 활용
"""

import requests
from bs4 import BeautifulSoup
import time
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 공공기관 알리미 평가위원 풀 (공개 데이터)
EVALUATOR_POOL_URL = "https://www.alio.go.kr/alio/site/main/publicinstitutions/evaluatorPool.do"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


@dataclass
class EvaluatorStat:
    company_name: str
    total_evaluators: int      # 전체 평가위원 풀 인원
    company_evaluators: int    # 해당 기업 소속 평가위원 수
    activity_rate_pct: float   # 활동률 (%)
    growth_score: float        # 성장 가능성 점수 (0~10)
    interpretation: str        # 해석 문구


def analyze_evaluator_activity(company_name: str, inst_code: str = None) -> EvaluatorStat:
    """
    평가위원 풀에서 해당 기업 임직원 비율 분석
    높을수록 = 외부 전문성 인정 = 성장 가능성 높음
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    total = 0
    company_count = 0

    try:
        params = {"searchKeyword": company_name}
        if inst_code:
            params["instCode"] = inst_code

        resp = session.get(EVALUATOR_POOL_URL, params=params, timeout=15)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")

        # 전체 카운트
        total_el = soup.select_one(".total-count, .board-total")
        if total_el:
            match = re.search(r"[\d,]+", total_el.get_text())
            total = int(match.group().replace(",", "")) if match else 0

        # 해당 기업 소속 카운트
        rows = soup.select("table.board-list tbody tr")
        for row in rows:
            org_cell = row.select("td")
            if len(org_cell) >= 3:
                org_name = org_cell[2].get_text(strip=True)
                if company_name in org_name or (inst_code and inst_code in org_name):
                    company_count += 1

        time.sleep(1.5)
    except Exception as e:
        logger.error(f"평가위원 분석 실패 {company_name}: {e}")
        total = 1000
        company_count = 0

    activity_rate = (company_count / total * 100) if total > 0 else 0

    # 성장 가능성 점수 (0~10)
    if activity_rate >= 5:
        score = 9.0
        interpretation = "전문성 매우 높음 — 외부 활동 활발, 이직 및 전문가 네트워크 구축 용이"
    elif activity_rate >= 2:
        score = 7.0
        interpretation = "전문성 높음 — 외부 평가 활동 보통 이상, 커리어 확장 가능"
    elif activity_rate >= 0.5:
        score = 5.0
        interpretation = "보통 — 외부 활동 제한적이나 내부 성장 구조 존재 가능"
    else:
        score = 3.0
        interpretation = "내부 중심 — 외부 노출 낮음, 안정적이나 전문성 인정 기회 적음"

    return EvaluatorStat(
        company_name=company_name,
        total_evaluators=total,
        company_evaluators=company_count,
        activity_rate_pct=round(activity_rate, 2),
        growth_score=score,
        interpretation=interpretation,
    )
