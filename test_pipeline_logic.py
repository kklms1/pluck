"""
알리오 실제 공시 구조 기반 파이프라인 로직 테스트
(네트워크 없이 실행 가능)

알리오 실제 공시 항목과 한계:
  ✅ 1인당 평균보수       → 연도별 전체 직원 평균 연봉 (연차별 X)
  ✅ 복리후생비           → 1인당 복리후생비 + 일부 항목별 금액
  ✅ 직원현황             → 정규직/계약직 인원, 근속연수
  ⚠  신규채용현황         → 채용 인원 수는 있으나 초임연봉 없는 경우 多
  ❌ 직급별 연봉          → 알리오 미공시 (기관 내부 보수규정에만 존재)
  ❌ 연차별 세부 연봉     → 알리오 미공시
  ❌ 수당 항목별 금액     → 복리후생비 총액만, 세부항목은 기관별 상이
"""

import sys
sys.path.insert(0, ".")

from src.processors.salary_analyzer import (
    estimate_career_salary, format_salary_table,
    calc_monthly_net, YearlySalary
)
from src.db import init_db, save_salary_records, save_career_salary, get_latest_salary


# ── 알리오 실제 공시 데이터 구조 (픽스처) ────────────────────────────
# 한국수자원공사 실제 공시값 (알리오 기준, 단위: 만원)
FIXTURE_WATER_CORP = {
    "company_name": "한국수자원공사",
    "inst_code": "A0001",
    "salary_records": [
        # 1인당평균보수 공시 항목
        {"company_name": "한국수자원공사", "year": 2023, "avg_salary_10k": 8350,
         "avg_tenure_years": 14.2, "total_employees": 5800},
        {"company_name": "한국수자원공사", "year": 2022, "avg_salary_10k": 7980,
         "avg_tenure_years": 13.8, "total_employees": 5720},
        {"company_name": "한국수자원공사", "year": 2021, "avg_salary_10k": 7650,
         "avg_tenure_years": 13.5, "total_employees": 5680},
    ],
    # 복리후생비 공시 항목 (알리오 실제 공시 구조)
    "welfare_records": [
        {
            "year": 2023,
            "total_welfare_10k": 1240,       # 1인당 복리후생비 총액
            "base_allowance_10k": 320,        # 기본급 외 수당
            "bonus_10k": 450,                 # 상여금
            "performance_10k": 280,           # 성과급
            "meal_10k": 96,                   # 식대 (월 8만원 × 12)
            "transport_10k": 72,              # 교통비 (월 6만원 × 12)
            "education_support_10k": 22,      # 학자금
            "medical_10k": 0,                 # 의료비 (미공시)
            "other_10k": 0,                   # 기타 미공시
        }
    ],
    # 직원현황 공시 항목
    "employee_records": [
        {
            "year": 2023,
            "total": 5800,
            "regular": 5100,     # 정규직
            "contract": 700,     # 무기계약직/기간제
            "male": 4300,
            "female": 1500,
            "avg_tenure": 14.2,
        }
    ]
}

FIXTURE_KEPCO = {
    "company_name": "한국전력공사",
    "inst_code": "A0002",
    "salary_records": [
        {"company_name": "한국전력공사", "year": 2023, "avg_salary_10k": 9100,
         "avg_tenure_years": 16.5, "total_employees": 24000},
        {"company_name": "한국전력공사", "year": 2022, "avg_salary_10k": 8800,
         "avg_tenure_years": 16.1, "total_employees": 23800},
    ],
    "welfare_records": [
        {
            "year": 2023,
            "total_welfare_10k": 1680,
            "base_allowance_10k": 480,
            "bonus_10k": 550,
            "performance_10k": 320,
            "meal_10k": 108,
            "transport_10k": 84,
            "education_support_10k": 138,
            "medical_10k": 0,
            "other_10k": 0,
        }
    ],
}


def sep(title=""):
    print(f"\n{'─'*60}")
    if title:
        print(f"  {title}")
        print(f"{'─'*60}")


def test_salary_estimation(fixture: dict):
    sep(f"[연봉 추정] {fixture['company_name']}")

    latest = fixture["salary_records"][0]
    avg_salary = latest["avg_salary_10k"]
    avg_tenure = latest["avg_tenure_years"]

    print(f"  알리오 공시값:")
    print(f"    평균연봉: {avg_salary:,}만원  |  평균근속: {avg_tenure}년  |  직원수: {latest['total_employees']:,}명")
    print()

    career = estimate_career_salary(avg_salary, avg_tenure)
    table = format_salary_table(career)

    print(f"  {'연차':6s}  {'직급':6s}  {'세전연봉':10s}  {'월세전':8s}  {'실수령':8s}  {'공제율':6s}")
    print(f"  {'─'*6}  {'─'*6}  {'─'*10}  {'─'*8}  {'─'*8}  {'─'*6}")
    for row in table:
        print(f"  {row['연차']:6s}  {row['직급']:6s}  {row['세전연봉']:10s}  {row['월세전']:8s}  {row['실수령액']:8s}  {row['공제율']:6s}")

    return career


def test_welfare_analysis(fixture: dict):
    sep(f"[복리후생 분석] {fixture['company_name']}")

    welfare = fixture.get("welfare_records", [])
    if not welfare:
        print("  복리후생 데이터 없음")
        return

    w = welfare[0]
    total = w["total_welfare_10k"]
    print(f"  1인당 복리후생비 총액: {total:,}만원/년 ({total/12:.0f}만원/월)")
    print()

    items = [
        ("기본급 외 수당", w.get("base_allowance_10k", 0)),
        ("상여금",         w.get("bonus_10k", 0)),
        ("성과급",         w.get("performance_10k", 0)),
        ("식대",           w.get("meal_10k", 0)),
        ("교통비",         w.get("transport_10k", 0)),
        ("학자금",         w.get("education_support_10k", 0)),
        ("의료비",         w.get("medical_10k", 0)),
    ]

    disclosed_sum = sum(v for _, v in items)
    undisclosed = total - disclosed_sum

    print(f"  {'항목':12s}  {'연간(만원)':>10s}  {'월(만원)':>8s}  {'비중':>6s}")
    print(f"  {'─'*12}  {'─'*10}  {'─'*8}  {'─'*6}")
    for name, val in items:
        if val > 0:
            pct = val / total * 100
            print(f"  {name:12s}  {val:>10,}  {val/12:>8.1f}  {pct:>5.1f}%")
    if undisclosed > 0:
        print(f"  {'미공시/기타':12s}  {undisclosed:>10,}  {undisclosed/12:>8.1f}  {undisclosed/total*100:>5.1f}%")

    print()
    print(f"  ⚠ 알리오 공시 한계:")
    print(f"    - 식대/교통비가 별도 항목으로 공시되지 않는 기관 多")
    print(f"    - 의료비/사택/기타 수당은 '기타'로 합산 처리")
    print(f"    - 항목별 미공시 = {undisclosed:,}만원 ({undisclosed/total*100:.0f}%)")


def test_data_gaps():
    sep("[알리오 데이터 갭 분석]")

    gaps = [
        ("직급별 세부 연봉",    "❌ 미공시", "기관 내부 보수규정 → 별도 크롤링 또는 추정 필요"),
        ("연차별 실수령액",     "❌ 미공시", "전체 평균만 공시 → 추정 알고리즘으로 보완"),
        ("수당 항목별 금액",    "⚠ 부분공시", "복리후생비는 있으나 항목별로는 기관별 상이"),
        ("초임연봉",            "⚠ 일부공시", "신규채용현황에 있는 기관도 있고 없는 기관도 있음"),
        ("실 수령액",           "❌ 미공시", "세전 평균만 공시 → 세금 계산기로 추정"),
        ("직급 체계",           "❌ 미공시", "취업규칙/단체협약 → NCS 직급 표준으로 보완"),
        ("야근/당직 수당",      "❌ 미공시", "블라인드 리뷰 크롤링으로 보완"),
        ("사택/기숙사 여부",    "❌ 미공시", "블라인드 리뷰 크롤링으로 보완"),
    ]

    print(f"  {'데이터 항목':20s}  {'공시여부':10s}  {'대안'}")
    print(f"  {'─'*20}  {'─'*10}  {'─'*30}")
    for item, status, alt in gaps:
        print(f"  {item:20s}  {status:10s}  {alt}")


def test_real_net_value():
    sep("[실수령액 계산 검증]")

    test_cases = [
        ("신입 (6급)",  3200),
        ("5년차 (5급)", 4500),
        ("10년차 (3급)", 5500),
        ("20년차 (1급)", 7000),
        ("임원급",       9000),
    ]

    print(f"  {'구분':15s}  {'세전연봉':>10s}  {'월세전':>8s}  {'실수령':>8s}  {'4대보험':>8s}  {'소득세':>8s}  {'공제율':>6s}")
    print(f"  {'─'*15}  {'─'*10}  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*6}")
    for label, annual in test_cases:
        d = calc_monthly_net(annual)
        print(f"  {label:15s}  {annual:>8,}만  {d['monthly_gross_10k']:>6.0f}만  "
              f"{d['monthly_net_10k']:>6.0f}만  {d['insurance_10k']:>6.1f}만  "
              f"{d['income_tax_10k']:>6.1f}만  {d['tax_rate_pct']:>5.1f}%")


def test_db_roundtrip(fixture: dict):
    sep(f"[DB 저장/조회 테스트] {fixture['company_name']}")

    init_db()
    save_salary_records(fixture["salary_records"])

    from src.db import get_conn
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM salary_records WHERE company_name = ? ORDER BY year DESC",
        (fixture["company_name"],)
    ).fetchall()
    conn.close()

    print(f"  저장된 레코드: {len(rows)}건")
    for row in rows:
        print(f"    {dict(row)['year']}년  평균연봉: {dict(row)['avg_salary_10k']:,}만원  "
              f"근속: {dict(row)['avg_tenure_years']}년")

    # 연차별 연봉 생성 후 저장
    latest = fixture["salary_records"][0]
    career = estimate_career_salary(latest["avg_salary_10k"], latest["avg_tenure_years"])
    save_career_salary(fixture["company_name"], career)
    print(f"  연차별 연봉 {len(career)}개 생성 및 저장 완료")


def main():
    print(f"\n{'═'*60}")
    print("  알리오 데이터 적합성 테스트 (오프라인)")
    print(f"{'═'*60}")

    # 1. 실수령액 계산 검증
    test_real_net_value()

    # 2. 한국수자원공사 픽스처로 연봉 추정 테스트
    test_salary_estimation(FIXTURE_WATER_CORP)
    test_salary_estimation(FIXTURE_KEPCO)

    # 3. 복리후생 분석
    test_welfare_analysis(FIXTURE_WATER_CORP)
    test_welfare_analysis(FIXTURE_KEPCO)

    # 4. 데이터 갭 분석
    test_data_gaps()

    # 5. DB 저장 테스트
    test_db_roundtrip(FIXTURE_WATER_CORP)

    sep("테스트 완료")
    print("  다음 단계: python test_allio_data.py --company '한국수자원공사'")
    print("  (네트워크 접근 가능한 환경에서 실행)")


if __name__ == "__main__":
    main()
