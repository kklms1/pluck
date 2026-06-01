"""
알리오 데이터 적합성 테스트
실행: python test_allio_data.py --company "한국수자원공사"

각 공시 카테고리별로 실제 접근 가능한 데이터와 URL을 탐색합니다.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import argparse
import sys
from dataclasses import dataclass, field
from typing import Optional

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Referer": "https://www.alio.go.kr",
    "Connection": "keep-alive",
})

BASE = "https://www.alio.go.kr"

# ── 알리오 공시 카테고리별 URL 패턴 ──────────────────────────────────
# 실제 알리오 경영공시 파라미터 구조 (instCode로 기관 구분)
DISCLOSURE_URLS = {
    "기관검색":         "/alio/site/main/publicinstitutions/publicInstSearch.do",
    "기관기본정보":     "/alio/site/main/publicinstitutions/publicInstDetail.do",
    "임원현황":         "/alio/site/main/publicinstitutions/publicOfficerList.do",
    "임원보수현황":     "/alio/site/main/publicinstitutions/officerSalaryInfo.do",
    "직원현황":         "/alio/site/main/publicinstitutions/employInfo.do",
    "신규채용현황":     "/alio/site/main/publicinstitutions/newHireInfo.do",
    "1인당평균보수":    "/alio/site/main/publicinstitutions/averageSalaryInfo.do",
    "복리후생비":       "/alio/site/main/publicinstitutions/welfareExpenseInfo.do",
    "교육훈련비":       "/alio/site/main/publicinstitutions/educationExpenseInfo.do",
    "노동조합현황":     "/alio/site/main/publicinstitutions/laborUnionInfo.do",
}

# 연봉/직급/복지 관련 핵심 필드 정의
EXPECTED_FIELDS = {
    "1인당평균보수": ["연도", "1인당평균보수", "1인당평균보수(정규직)", "1인당평균보수(무기계약직)"],
    "직원현황":     ["연도", "정원", "현원", "남", "여", "정규직", "무기계약직", "기간제"],
    "복리후생비":   ["연도", "복리후생비", "1인당복리후생비", "기본급외수당", "상여금", "성과급",
                     "식대", "교통비", "학자금", "의료비", "기타"],
    "신규채용현황": ["연도", "채용인원", "초임연봉", "정규직채용"],
    "임원보수현황": ["연도", "임원수", "기관장보수", "평균임원보수"],
}


@dataclass
class ProbeResult:
    category: str
    url: str
    http_status: int
    accessible: bool
    fields_found: list[str] = field(default_factory=list)
    fields_missing: list[str] = field(default_factory=list)
    sample_data: list[dict] = field(default_factory=list)
    raw_tables: int = 0
    error: Optional[str] = None


def probe_page(category: str, path: str, inst_code: str) -> ProbeResult:
    url = BASE + path
    result = ProbeResult(category=category, url=url, http_status=0, accessible=False)

    try:
        resp = SESSION.get(url, params={"instCode": inst_code}, timeout=15)
        result.http_status = resp.status_code
        time.sleep(1.2)

        if resp.status_code != 200:
            result.error = f"HTTP {resp.status_code}"
            return result

        result.accessible = True
        soup = BeautifulSoup(resp.text, "lxml")

        tables = soup.select("table")
        result.raw_tables = len(tables)

        # 테이블 헤더 추출
        all_headers = []
        for table in tables:
            headers = [th.get_text(strip=True) for th in table.select("th")]
            all_headers.extend(headers)

        # 기대 필드 매칭
        expected = EXPECTED_FIELDS.get(category, [])
        result.fields_found = [f for f in expected if any(f in h for h in all_headers)]
        result.fields_missing = [f for f in expected if f not in result.fields_found]

        # 샘플 데이터 (첫 번째 테이블 최대 3행)
        for table in tables[:2]:
            rows = table.select("tbody tr")
            for row in rows[:3]:
                cols = [td.get_text(strip=True) for td in row.select("td")]
                if cols and any(cols):
                    result.sample_data.append(cols)

    except requests.RequestException as e:
        result.error = str(e)

    return result


def search_company(name: str) -> Optional[str]:
    """기관명으로 기관코드 검색"""
    url = BASE + DISCLOSURE_URLS["기관검색"]
    try:
        resp = SESSION.get(url, params={"searchKeyword": name, "pageIndex": 1}, timeout=15)
        time.sleep(1.2)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # href에서 instCode 추출
        import re
        links = soup.select("a[href*='instCode']")
        for link in links:
            href = link.get("href", "")
            match = re.search(r"instCode[=']([A-Z0-9]+)", href)
            if match:
                return match.group(1)

        # JavaScript onclick에서 추출
        for tag in soup.select("[onclick*='instCode']"):
            onclick = tag.get("onclick", "")
            match = re.search(r"instCode[=',]([A-Z0-9]+)", onclick)
            if match:
                return match.group(1)

    except Exception as e:
        print(f"  검색 오류: {e}")
    return None


def print_result(r: ProbeResult, verbose: bool = False):
    status_icon = "✅" if r.accessible else "❌"
    print(f"\n{status_icon} [{r.category}]")
    print(f"   URL: {r.url}")
    print(f"   HTTP: {r.http_status}  |  테이블 수: {r.raw_tables}")

    if r.error:
        print(f"   오류: {r.error}")
        return

    if r.fields_found:
        print(f"   ✔ 확인된 필드: {', '.join(r.fields_found)}")
    if r.fields_missing:
        print(f"   ✘ 누락 필드:   {', '.join(r.fields_missing)}")

    if verbose and r.sample_data:
        print("   샘플 데이터:")
        for row in r.sample_data[:3]:
            print(f"     {row}")


def run_test(company_name: str, verbose: bool = False):
    print(f"\n{'═'*60}")
    print(f"  알리오 데이터 적합성 테스트: {company_name}")
    print(f"{'═'*60}")

    # Step 1: 기관코드 탐색
    print(f"\n[1/3] 기관코드 탐색 중...")
    inst_code = search_company(company_name)
    if inst_code:
        print(f"  기관코드: {inst_code}")
    else:
        print("  ⚠ 기관코드 자동 탐색 실패 — 수동으로 --inst-code 지정 필요")
        inst_code = "UNKNOWN"

    # Step 2: 카테고리별 프로브
    print(f"\n[2/3] 공시 카테고리 탐색 중...")
    results = {}
    target_categories = [k for k in DISCLOSURE_URLS if k != "기관검색" and k != "기관기본정보"]

    for cat in target_categories:
        path = DISCLOSURE_URLS[cat]
        r = probe_page(cat, path, inst_code)
        results[cat] = r
        print_result(r, verbose=verbose)

    # Step 3: 종합 판정
    print(f"\n[3/3] 종합 데이터 적합성 판정")
    print(f"{'─'*60}")

    accessible = [k for k, v in results.items() if v.accessible]
    blocked = [k for k, v in results.items() if not v.accessible]

    print(f"접근 가능: {len(accessible)}/{len(results)} 카테고리")
    print(f"접근 불가: {blocked}" if blocked else "접근 불가: 없음")

    # 핵심 데이터 가용성 평가
    print(f"\n{'─'*60}")
    print("  영상 제작에 필요한 데이터 평가")
    print(f"{'─'*60}")

    checks = [
        ("연봉 데이터",     "1인당평균보수",  "★★★ 핵심 — 연차별 추정 기반"),
        ("직원 구성",       "직원현황",       "★★☆ 직종별/성별 구성"),
        ("복지/수당",       "복리후생비",     "★★★ 핵심 — 블라인드 대체 가능"),
        ("신입 초봉",       "신규채용현황",   "★★★ 핵심 — 직접 공시 여부"),
        ("임원 보수",       "임원보수현황",   "★☆☆ 참고용"),
        ("노조 현황",       "노동조합현황",   "★☆☆ 참고용"),
    ]

    for label, cat, importance in checks:
        r = results.get(cat)
        if not r:
            icon = "?"
        elif not r.accessible:
            icon = "❌"
        elif r.sample_data:
            icon = "✅"
        else:
            icon = "⚠ (접근됨, 데이터 없음)"
        print(f"  {icon} {label:12s} [{importance}]")

    # JSON 저장
    output = {
        "company": company_name,
        "inst_code": inst_code,
        "results": {
            k: {
                "accessible": v.accessible,
                "http_status": v.http_status,
                "fields_found": v.fields_found,
                "fields_missing": v.fields_missing,
                "sample_rows": len(v.sample_data),
                "error": v.error,
            }
            for k, v in results.items()
        }
    }
    out_path = f"data/allio_probe_{company_name.replace(' ', '_')}.json"
    import os
    os.makedirs("data", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", "-c", required=True, help="기업명 (예: 한국수자원공사)")
    parser.add_argument("--inst-code", help="알리오 기관코드 (자동 탐색 실패 시)")
    parser.add_argument("--verbose", "-v", action="store_true", help="샘플 데이터 출력")
    args = parser.parse_args()

    run_test(args.company, verbose=args.verbose)
