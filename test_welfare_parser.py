"""
복지/휴가/교육 파서 로직 테스트 (오프라인)
"""
import sys
sys.path.insert(0, ".")

from src.processors.welfare_parser import (
    parse_welfare_tables, parse_training_tables,
    parse_union_tables, parse_leave_policy,
    WelfareSummary, TrainingSummary, LeavePolicy,
)

# ── 알리오 복리후생비 공시 픽스처 ─────────────────────────────────────
# 실제 알리오 테이블 구조 모사
WELFARE_TABLE = [
    ["연도", "합계", "식대", "교통비", "의료비", "학자금", "주택", "복지포인트", "기타"],
    ["2023", "1,240", "96",  "72",  "45",  "88",  "120", "180", "639"],
    ["2022", "1,180", "96",  "72",  "40",  "80",  "115", "160", "617"],
    ["2021", "1,100", "96",  "66",  "38",  "75",  "110", "145", "570"],
]

TRAINING_TABLE = [
    ["연도", "합계", "1인당", "국내", "해외"],
    ["2023", "4,800", "82.7",  "3,200", "1,600"],
    ["2022", "4,200", "73.4",  "2,900", "1,300"],
    ["2021", "2,100", "36.9",  "1,800",   "300"],
]

UNION_TABLE = [
    ["연도", "노동조합명", "조합원수", "전체직원", "가입률"],
    ["2023", "한국수자원공사노동조합", "4,850", "5,800", "83.6"],
    ["2022", "한국수자원공사노동조합", "4,760", "5,720", "83.2"],
]

# ── 취업규칙 텍스트 픽스처 ─────────────────────────────────────────────
WORKPLACE_RULES_TEXT = """
제40조(연차유급휴가)
① 1년 이상 근속한 직원에게는 근속연수에 따라 다음과 같이 연차유급휴가를 부여한다.
  - 1년 이상 3년 미만: 15일
  - 3년 이상 5년 미만: 17일
  - 5년 이상 10년 미만: 19일
  - 10년 이상 20년 미만: 22일
  - 20년 이상: 25일

제41조(하계휴가)
회사는 매년 하계에 7일의 하계휴가를 별도로 부여할 수 있다.

제42조(병가)
① 업무 외 질병·부상으로 인한 유급 병가는 연간 60일 이내로 한다.
② 유급 병가 소진 후 추가로 필요한 경우 무급 병가 90일을 부여할 수 있다.

제48조(육아휴직)
① 만 8세 이하 자녀를 둔 직원은 최대 24개월의 육아휴직을 사용할 수 있다.
② 육아휴직 기간 중 첫 3개월은 통상임금의 80%를 지급한다.

제50조(경조사 휴가)
결혼: 5일, 배우자 출산: 10일, 부모사망: 5일, 배우자사망: 5일

제55조(유연근무제)
회사는 직원의 업무효율 향상을 위해 시차출퇴근제, 선택적근로시간제 등
유연근무제를 운영하며 세부사항은 별도로 정한다.

제56조(재택근무)
직원은 업무의 성격 및 상황에 따라 주 2일 이내로 재택근무를 신청할 수 있다.
부서장의 승인 하에 재택근무가 가능하며, 재택근무 시에도 동일한 업무 의무가 적용된다.

제60조(해외연수)
① 회사는 직원의 글로벌 역량 강화를 위해 해외연수 프로그램을 운영한다.
② 근속 5년 이상인 직원 중 선발하여 해외 전문교육기관에 1년 이내 파견할 수 있다.
③ 어학연수: 영어·일어·중국어 어학연수 비용의 50% 지원 (연간 최대 200만원)
④ MBA 지원: 사내 선발 절차를 거쳐 국내외 MBA 학위과정 지원 가능

제62조(학습휴직)
직원이 학위취득 또는 자격증 취득 등 자기계발 목적으로 신청하는 경우
최대 2년의 학습휴직을 허가할 수 있다.
"""


def sep(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print("─" * 60)


def test_welfare():
    sep("복리후생비 파서 테스트")
    results = parse_welfare_tables("한국수자원공사", [WELFARE_TABLE])
    for w in results:
        print(f"  {w.year}년  총액: {w.total_per_person_10k:,.0f}만원/년 "
              f"({w.total_per_person_10k/12:.0f}만원/월)")
        if w.meal_10k:      print(f"    식대:       {w.meal_10k:6.0f}만/년")
        if w.transport_10k: print(f"    교통비:     {w.transport_10k:6.0f}만/년")
        if w.medical_10k:   print(f"    의료비:     {w.medical_10k:6.0f}만/년")
        if w.childcare_tuition_10k:
                            print(f"    학자금:     {w.childcare_tuition_10k:6.0f}만/년")
        if w.housing_loan_10k:
                            print(f"    주택:       {w.housing_loan_10k:6.0f}만/년")
        if w.welfare_point_10k:
                            print(f"    복지포인트: {w.welfare_point_10k:6.0f}만/년")
    assert len(results) == 3
    assert results[0].meal_10k == 96
    print("  ✅ PASS")


def test_training():
    sep("교육훈련비 파서 테스트")
    results = parse_training_tables("한국수자원공사", [TRAINING_TABLE])
    for t in results:
        print(f"  {t.year}년  총액: {t.total_10k:,.0f}만원  "
              f"1인당: {t.per_person_10k:.1f}만원  "
              f"해외: {t.overseas_expense_10k:,.0f}만원")
    assert len(results) == 3
    assert results[0].overseas_expense_10k == 1600
    print("  ✅ PASS")


def test_union():
    sep("노동조합 파서 테스트")
    results = parse_union_tables("한국수자원공사", [UNION_TABLE])
    for u in results:
        print(f"  {u.year}년  {u.union_name}  "
              f"조합원 {u.member_count:,}명  가입률 {u.union_rate_pct:.1f}%")
    assert len(results) == 2
    assert results[0].union_rate_pct == 83.6
    print("  ✅ PASS")


def test_leave_policy():
    sep("취업규칙 휴가정책 파서 테스트")
    policy = parse_leave_policy(WORKPLACE_RULES_TEXT, "한국수자원공사", "fixture")

    checks = [
        ("연차 최소", policy.annual_leave_min, 15),
        ("연차 최대", policy.annual_leave_max, 25),
        ("하계휴가", policy.summer_leave_days, 7),
        ("유급병가", policy.sick_paid_days, 60),
        ("무급병가", policy.sick_unpaid_days, 90),
        ("육아휴직", policy.parental_leave_months, 24),
        ("결혼휴가", policy.marriage_days, 5),
        ("유연근무", policy.flexible_work, True),
        ("재택근무", policy.remote_work, True),
        ("해외연수", policy.overseas_training, True),
        ("어학연수", policy.language_training, True),
        ("MBA지원", policy.mba_support, True),
        ("학습휴직", policy.study_leave, True),
    ]

    all_pass = True
    for label, actual, expected in checks:
        ok = actual == expected
        icon = "✅" if ok else f"❌ (기대:{expected}, 실제:{actual})"
        print(f"  {label:12s}: {actual}  {icon}")
        if not ok:
            all_pass = False

    if all_pass:
        print("\n  ✅ ALL PASS")
    else:
        print("\n  ⚠ 일부 파싱 실패 — 정규식 패턴 조정 필요")

    return policy


def summary(policy: LeavePolicy):
    sep("영상 콘텐츠 요약 포인트")
    print(f"""
  [연봉 외 핵심 복지]
  ✔ 연차:          {policy.annual_leave_min}~{policy.annual_leave_max}일 (법정 15일 + α)
  ✔ 하계휴가:      {policy.summer_leave_days}일 별도 (사실상 연간 {policy.annual_leave_max + policy.summer_leave_days}일)
  ✔ 유급병가:      {policy.sick_paid_days}일
  ✔ 육아휴직:      최대 {policy.parental_leave_months}개월
  ✔ 결혼휴가:      {policy.marriage_days}일
  ✔ 유연근무:      {'있음' if policy.flexible_work else '없음'}
  ✔ 재택근무:      {'있음' if policy.remote_work else '없음'}
  ✔ 해외연수:      {'있음' if policy.overseas_training else '없음'}
  ✔ 어학연수:      {'있음' if policy.language_training else '없음'}
  ✔ MBA 지원:      {'있음' if policy.mba_support else '없음'}
  ✔ 학습휴직:      {'있음' if policy.study_leave else '없음'}
    """)


def main():
    print(f"\n{'═'*60}")
    print("  복지/휴가/교육 파서 테스트 (오프라인)")
    print(f"{'═'*60}")

    test_welfare()
    test_training()
    test_union()
    policy = test_leave_policy()
    summary(policy)


if __name__ == "__main__":
    main()
