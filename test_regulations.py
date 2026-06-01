"""
한국전력공사 보수규정 크롤링 + 연봉 산정 테스트
실행: python test_regulations.py

알리오 내부공시 URL:
  https://alio.go.kr/mobile/organ/organDisclosureDtl.do?apbaId=C0247
"""

import sys
import logging
import json
from pathlib import Path

sys.path.insert(0, ".")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

from src.crawlers.allio_regulations import AlioRegulationCrawler
from src.processors.regulation_parser import parse_regulation_file
from src.processors.salary_from_hobong import build_career_table, format_career_table

COMPANY_NAME = "한국전력공사"
APBA_ID = "C0247"    # 알리오 내부공시 apbaId


def sep(title=""):
    print(f"\n{'═' if not title else '─'*60}")
    if title:
        print(f"  {title}")
        print("─" * 60)


def step1_crawl():
    sep(f"STEP 1 — 내부규정 파일 다운로드 ({COMPANY_NAME})")
    crawler = AlioRegulationCrawler(delay=1.5)
    files = crawler.collect(COMPANY_NAME, APBA_ID)

    if not files:
        print("  ⚠ 규정 파일 다운로드 실패")
        print("  가능한 원인:")
        print("    1. 알리오 세션 쿠키 필요 (브라우저에서 먼저 접속 후 재시도)")
        print("    2. apbaId 확인 필요 (현재: C0247)")
        print("    3. 네트워크 방화벽")
        print()
        print("  수동 다운로드 후 테스트하려면:")
        print("    data/regulations/ 폴더에 PDF 저장 후")
        print("    python test_regulations.py --local")
        return []

    print(f"  다운로드 완료: {len(files)}개")
    for f in files:
        print(f"    - {f.name} → {f.local_path}")
    return files


def step2_parse(files):
    sep("STEP 2 — 보수규정 파싱 (호봉 테이블 추출)")
    results = []

    for f in files:
        if not f.local_path or not Path(f.local_path).exists():
            continue
        if not any(kw in f.name for kw in ["보수", "인사", "취업"]):
            continue

        print(f"\n  [{f.name}] 파싱 중...")
        parsed = parse_regulation_file(f.local_path, COMPANY_NAME)

        print(f"    호봉행: {len(parsed.hobong_rows)}개")
        print(f"    수당:   {len(parsed.allowances)}개")
        print(f"    신뢰도: {parsed.parse_quality:.0%}")

        if parsed.hobong_rows:
            # 직급별 호봉 샘플 출력
            by_grade: dict = {}
            for row in parsed.hobong_rows:
                by_grade.setdefault(row.grade, []).append(row)

            for grade, rows in sorted(by_grade.items()):
                rows_sorted = sorted(rows, key=lambda r: r.hobong)
                sample = rows_sorted[:3]
                sample_str = "  ".join(f"{r.hobong}호봉={r.base_salary_10k:,}만" for r in sample)
                print(f"    {grade}: {sample_str} ...")

        if parsed.allowances:
            print(f"    수당 항목: {dict(list(parsed.allowances.items())[:5])}")

        results.append(parsed)

    return results


def step3_salary_table(parsed_list):
    sep("STEP 3 — 연차별 연봉/실수령 테이블")

    all_points = []
    for parsed in parsed_list:
        points = build_career_table(parsed)
        if points:
            all_points = points
            break

    if not all_points:
        print("  ⚠ 호봉 테이블 없음 — 추정 모드 사용")
        return

    table = format_career_table(all_points)
    print(f"\n  {COMPANY_NAME} 연차별 연봉 (보수규정 기반)\n")
    print(f"  {'연차':6s}  {'직급':5s}  {'호봉':5s}  {'기본급':8s}  {'세전연봉':10s}  {'월세전':7s}  {'실수령':7s}  {'공제율':5s}")
    print(f"  {'─'*6}  {'─'*5}  {'─'*5}  {'─'*8}  {'─'*10}  {'─'*7}  {'─'*7}  {'─'*5}")
    for row in table:
        print(f"  {row['연차']:6s}  {row['직급']:5s}  {row['호봉']:5s}  "
              f"{row['기본급']:8s}  {row['세전연봉']:10s}  {row['월세전']:7s}  "
              f"{row['실수령']:7s}  {row['공제율']:5s}")

    # JSON 저장
    out = Path("data") / f"{COMPANY_NAME}_career_salary_hobong.json"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump([p.__dict__ for p in all_points], f, ensure_ascii=False, indent=2)
    print(f"\n  저장: {out}")


def step_local_test():
    """data/regulations/ 에 이미 다운로드된 파일로 테스트"""
    sep("로컬 파일 테스트")
    reg_dir = Path("data/regulations")
    files = list(reg_dir.glob("*.pdf")) + list(reg_dir.glob("*.hwp*"))

    if not files:
        print(f"  {reg_dir}/ 에 파일 없음")
        print("  알리오에서 보수규정 PDF를 수동으로 다운로드 후 넣어주세요.")
        return

    from src.processors.regulation_parser import parse_regulation_file
    parsed_list = []
    for f in files:
        print(f"\n  파싱: {f.name}")
        parsed = parse_regulation_file(str(f), COMPANY_NAME)
        parsed_list.append(parsed)
        print(f"    호봉행: {len(parsed.hobong_rows)}, 수당: {len(parsed.allowances)}, 신뢰도: {parsed.parse_quality:.0%}")

    step3_salary_table(parsed_list)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", action="store_true", help="다운로드 건너뛰고 로컬 파일로 테스트")
    parser.add_argument("--apba-id", default=APBA_ID, help="알리오 apbaId (기본: C0247)")
    args = parser.parse_args()

    print(f"\n{'═'*60}")
    print(f"  {COMPANY_NAME} 보수규정 기반 연봉 산정 테스트")
    print(f"  알리오 내부공시: apbaId={args.apba_id}")
    print(f"{'═'*60}")

    if args.local:
        step_local_test()
        return

    files = step1_crawl()
    parsed_list = step2_parse(files)
    step3_salary_table(parsed_list)


if __name__ == "__main__":
    main()
