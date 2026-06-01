"""
공기업 전체 데이터 수집 스크립트 (로컬 실행용)

사용법:
  python crawl_company.py --company "한국전력공사" --inst-code A0009 --apba-id C0247
  python crawl_company.py --company "한국수자원공사" --inst-code A0003 --apba-id C0060
  python crawl_company.py --list   # 지원 기업 목록

수집 항목:
  ① 공시 데이터: 평균보수, 복리후생비, 교육훈련비, 노동조합, 직원현황
  ② 내부규정 파일: 보수규정(호봉표), 취업규칙(휴가/복지), 인사규정
  ③ 분석 결과: 연차별 연봉, 수당 구성, 휴가정책, 복지 수치

실행 전 준비:
  pip install playwright playwright-stealth pdfplumber
  playwright install chromium
"""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, ".")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("crawl")

# ── 알리오 기관 코드 사전 ─────────────────────────────────────────────
# inst_code: 알리오 경영공시 코드
# apba_id:   알리오 내부공시 apbaId (URL에서 확인)
COMPANY_CODES = {
    "한국전력공사":       {"inst_code": "A0009", "apba_id": "C0247"},
    "한국수자원공사":     {"inst_code": "A0003", "apba_id": "C0060"},
    "한국가스공사":       {"inst_code": "A0010", "apba_id": "C0248"},
    "한국토지주택공사":   {"inst_code": "A0001", "apba_id": "C0001"},
    "국민건강보험공단":   {"inst_code": "B0001", "apba_id": "C0100"},
    "한국도로공사":       {"inst_code": "A0006", "apba_id": "C0165"},
    "한국철도공사":       {"inst_code": "A0007", "apba_id": "C0177"},
    "한국공항공사":       {"inst_code": "A0013", "apba_id": "C0251"},
    "인천국제공항공사":   {"inst_code": "A0014", "apba_id": "C0252"},
    "한국마사회":         {"inst_code": "A0020", "apba_id": "C0258"},
    "국민연금공단":       {"inst_code": "B0002", "apba_id": "C0101"},
    "근로복지공단":       {"inst_code": "B0003", "apba_id": "C0102"},
    "한국원자력환경공단": {"inst_code": "A0025", "apba_id": "C0263"},
    "한국환경공단":       {"inst_code": "A0030", "apba_id": "C0268"},
    "한국농어촌공사":     {"inst_code": "A0031", "apba_id": "C0269"},
}


def print_table(data: dict):
    """분석 결과 터미널 출력"""
    company = data.get("company", "")
    sep = "═" * 70

    print(f"\n{sep}")
    print(f"  {company}  수집 결과")
    print(sep)

    # 복리후생비
    welfare_list = data.get("welfare", [])
    if welfare_list:
        w = welfare_list[0]
        print(f"\n  [복리후생비] (최근 {w.get('year')}년)")
        print(f"    1인당 총액:    {w.get('total_per_person_10k', 0):,.0f}만원/년")
        items = [
            ("식대",         "meal_10k"),
            ("교통비",       "transport_10k"),
            ("의료비/건강검진", "medical_10k"),
            ("학자금/보육",  "childcare_tuition_10k"),
            ("주택/사택",    "housing_loan_10k"),
            ("문화/여가",    "recreation_10k"),
            ("복지포인트",   "welfare_point_10k"),
        ]
        for label, key in items:
            val = w.get(key, 0)
            if val:
                print(f"    {label:12s}  {val:6.1f}만원/년  ({val/12:.1f}만원/월)")

    # 교육훈련비
    training_list = data.get("training", [])
    if training_list:
        t = training_list[0]
        print(f"\n  [교육훈련비] (최근 {t.get('year')}년)")
        print(f"    1인당:         {t.get('per_person_10k', 0):,.1f}만원/년")
        if t.get("overseas_expense_10k"):
            print(f"    해외연수 비용: {t.get('overseas_expense_10k', 0):,.1f}만원")
        if t.get("overseas_trainees"):
            print(f"    해외 파견인원: {t.get('overseas_trainees', 0):,}명")

    # 노동조합
    union = data.get("union")
    if union:
        print(f"\n  [노동조합]")
        print(f"    {union.get('union_name', '')}")
        print(f"    가입률: {union.get('union_rate_pct', 0):.1f}%  "
              f"({union.get('member_count', 0):,}명/{union.get('total_employees', 0):,}명)")

    # 휴가 정책
    leave = data.get("leave")
    if leave:
        print(f"\n  [휴가/복지 정책]  (취업규칙 기준)")
        print(f"    연차:       {leave.get('annual_leave_min',0)}일 ~ {leave.get('annual_leave_max',0)}일")
        if leave.get("summer_leave_days"):
            print(f"    하계휴가:   {leave['summer_leave_days']}일 (연차 외)")
        if leave.get("sick_paid_days"):
            print(f"    유급병가:   {leave['sick_paid_days']}일")
        print(f"    육아휴직:   {leave.get('parental_leave_months',0)}개월")
        print(f"    경조휴가:   결혼 {leave.get('marriage_days',0)}일, "
              f"조위 {leave.get('bereavement_days',0)}일")
        flags = []
        if leave.get("flexible_work"):   flags.append("유연근무✅")
        if leave.get("remote_work"):     flags.append("재택근무✅")
        if leave.get("overseas_training"): flags.append("해외연수✅")
        if leave.get("language_training"): flags.append("어학연수✅")
        if leave.get("mba_support"):     flags.append("MBA지원✅")
        if leave.get("study_leave"):     flags.append("학습휴직✅")
        if leave.get("career_break"):    flags.append("리프레시휴직✅")
        if flags:
            print(f"    특이사항:   {' / '.join(flags)}")

    print(f"\n{sep}\n")


def run(company_name: str, inst_code: str, apba_id: str,
        headless: bool = True, no_download: bool = False):
    from src.crawlers.allio_playwright import run as playwright_run
    from src.processors.welfare_parser import analyze_crawled_data, extract_leave_from_file
    from src.processors.regulation_parser import parse_regulation_file
    from src.processors.salary_from_hobong import build_career_table, format_career_table

    logger.info(f"\n{'='*50}")
    logger.info(f"  수집 시작: {company_name}")
    logger.info(f"  inst_code={inst_code}  apba_id={apba_id}")
    logger.info(f"{'='*50}")

    # 1. Playwright 크롤링
    logger.info("① Playwright 크롤링...")
    crawled = playwright_run(
        company_name=company_name,
        inst_code=inst_code,
        apba_id=apba_id,
        headless=headless,
        download_regulations=not no_download,
    )

    # 2. 공시 데이터 분석
    logger.info("② 공시 데이터 분석...")
    analysis = analyze_crawled_data(company_name, crawled)

    # 3. 내부규정 파싱 (보수규정 + 취업규칙)
    reg_files = crawled.get("regulation_files", [])
    if reg_files:
        logger.info(f"③ 내부규정 파싱 ({len(reg_files)}개)...")

        for rf in reg_files:
            local_path = rf.get("local_path", "")
            if not local_path or not Path(local_path).exists():
                continue

            name = rf.get("name", "")

            # 보수규정 → 호봉 테이블
            if any(kw in name for kw in ["보수규정", "보수기준", "보수세칙"]):
                logger.info(f"  보수규정 파싱: {Path(local_path).name}")
                parsed = parse_regulation_file(local_path, company_name)
                if parsed.hobong_rows:
                    from dataclasses import asdict
                    points = build_career_table(parsed, max_years=30)
                    analysis["career_salary"] = format_career_table(points)
                    analysis["career_points"] = [asdict(p) for p in points]  # raw 수치(카드/대본용)
                    analysis["allowances"] = dict(parsed.allowances)
                    analysis["allowance_ratios"] = dict(parsed.allowance_ratios)

            # 취업규칙 → 휴가/복지 정책
            elif any(kw in name for kw in ["취업규칙", "인사규정", "복무규정"]):
                logger.info(f"  취업규칙 파싱: {Path(local_path).name}")
                leave = extract_leave_from_file(local_path, company_name)
                if leave:
                    from dataclasses import asdict
                    analysis["leave"] = asdict(leave)

    # 4. 결과 출력 및 저장
    print_table(analysis)

    out_path = Path("data") / f"{company_name}_analysis.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    logger.info(f"결과 저장: {out_path}")

    return analysis


def main():
    parser = argparse.ArgumentParser(description="공기업 알리오 전체 데이터 수집")
    parser.add_argument("--company", "-c", help="기업명")
    parser.add_argument("--inst-code", help="알리오 경영공시 기관코드")
    parser.add_argument("--apba-id", help="알리오 내부공시 apbaId")
    parser.add_argument("--show", action="store_true", help="비헤드리스 모드 (브라우저 보이게)")
    parser.add_argument("--no-download", action="store_true", help="규정 파일 다운로드 건너뜀")
    parser.add_argument("--list", action="store_true", help="지원 기업 목록 출력")
    args = parser.parse_args()

    if args.list:
        print("\n지원 기업 목록:")
        for name, codes in COMPANY_CODES.items():
            print(f"  {name:15s}  inst={codes['inst_code']}  apba={codes['apba_id']}")
        print("\n사용 예:")
        print("  python crawl_company.py --company '한국전력공사'")
        return

    if not args.company:
        parser.print_help()
        return

    # 코드 자동 조회
    codes = COMPANY_CODES.get(args.company, {})
    inst_code = args.inst_code or codes.get("inst_code", "")
    apba_id = args.apba_id or codes.get("apba_id", "")

    if not inst_code:
        print(f"⚠ '{args.company}'의 inst_code를 모릅니다.")
        print("  --inst-code 직접 입력 또는 --list로 목록 확인")
        sys.exit(1)

    run(
        company_name=args.company,
        inst_code=inst_code,
        apba_id=apba_id,
        headless=not args.show,
        no_download=args.no_download,
    )


if __name__ == "__main__":
    main()
