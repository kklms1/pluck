"""
한국전력공사 보수규정 픽스처 기반 테스트
(실제 보수규정 공개 데이터 기반 호봉 테이블 사용)

한전 보수규정 실제 구조:
  - 직급: 6E(신입) ~ 1E(최고), 별도 임원급
  - 호봉제: 입사 1호봉, 매년 1호봉 승급
  - 직급 이동: 6E(1~3년) → 5E(3~7년) → 4E(7~12년) → ...
  - 수당: 직급보조비, 명절상여(기본급 100%), 성과급(기본급 200~500%)
"""

import sys
sys.path.insert(0, ".")

from src.processors.regulation_parser import ParsedSalaryTable, HobongRow
from src.processors.salary_from_hobong import build_career_table, format_career_table


# ── 한전 보수규정 호봉 테이블 픽스처 ─────────────────────────────────
# 출처: 알리오 공개 보수규정 기반 (실제 수치와 근사값)
# 단위: 만원 (기본급만, 수당 별도)
KEPCO_HOBONG = {
    "6급": {  # 6E 신입
        1: 215, 2: 222, 3: 229, 4: 236, 5: 243,
        6: 250, 7: 257, 8: 264, 9: 271, 10: 278,
    },
    "5급": {  # 5E
        1: 255, 2: 263, 3: 271, 4: 279, 5: 287,
        6: 295, 7: 303, 8: 311, 9: 319, 10: 327,
        11: 335, 12: 343,
    },
    "4급": {  # 4E
        1: 302, 2: 311, 3: 320, 4: 329, 5: 338,
        6: 347, 7: 356, 8: 365, 9: 374, 10: 383,
        11: 392, 12: 401, 13: 410, 14: 419,
    },
    "3급": {  # 3E
        1: 358, 2: 368, 3: 378, 4: 388, 5: 398,
        6: 408, 7: 418, 8: 428, 9: 438, 10: 448,
        11: 458, 12: 468, 13: 478, 14: 488, 15: 498,
    },
    "2급": {  # 2E
        1: 418, 2: 429, 3: 440, 4: 451, 5: 462,
        6: 473, 7: 484, 8: 495, 9: 506, 10: 517,
        11: 528, 12: 539, 13: 550, 14: 561, 15: 572,
    },
    "1급": {  # 1E (부장/처장)
        1: 492, 2: 504, 3: 516, 4: 528, 5: 540,
        6: 552, 7: 564, 8: 576, 9: 588, 10: 600,
    },
}

# 한전 수당 픽스처
# allowances  = 월 고정 금액 (만원), 직급·성과 무관
# allowance_ratios = 연간 기본급 배수 (성과급 3.0 = 기본급×300%/년)
KEPCO_ALLOWANCES = {
    "직급보조비":  15.0,
    "식대":        14.0,
    "교통비":       8.0,
    "가족수당":     4.0,
    "복지포인트":   5.0,
}
KEPCO_ALLOWANCE_RATIOS = {
    "명절상여":   2.0,   # 기본급 × 200%/년 (설·추석 각 100%)
    "성과급":     3.0,   # 기본급 × 300%/년 (경영성과급 포함 최저 추정)
}


def make_kepco_fixture() -> ParsedSalaryTable:
    rows = []
    for grade, hobong_dict in KEPCO_HOBONG.items():
        for hobong, base in hobong_dict.items():
            rows.append(HobongRow(grade=grade, hobong=hobong, base_salary=base))

    return ParsedSalaryTable(
        company_name="한국전력공사",
        source_file="fixture:kepco_bosugyu_2024",
        hobong_rows=rows,
        allowances=KEPCO_ALLOWANCES,
        allowance_ratios=KEPCO_ALLOWANCE_RATIOS,
        parse_quality=0.95,
    )


# ── 한국수자원공사 픽스처 ──────────────────────────────────────────────
KWater_HOBONG = {
    "6급": {
        1: 202, 2: 209, 3: 216, 4: 223, 5: 230,
        6: 237, 7: 244, 8: 251, 9: 258, 10: 265,
    },
    "5급": {
        1: 241, 2: 249, 3: 257, 4: 265, 5: 273,
        6: 281, 7: 289, 8: 297, 9: 305, 10: 313,
        11: 321, 12: 329,
    },
    "4급": {
        1: 288, 2: 297, 3: 306, 4: 315, 5: 324,
        6: 333, 7: 342, 8: 351, 9: 360, 10: 369,
        11: 378, 12: 387, 13: 396,
    },
    "3급": {
        1: 341, 2: 351, 3: 361, 4: 371, 5: 381,
        6: 391, 7: 401, 8: 411, 9: 421, 10: 431,
        11: 441, 12: 451, 13: 461, 14: 471,
    },
    "2급": {
        1: 398, 2: 409, 3: 420, 4: 431, 5: 442,
        6: 453, 7: 464, 8: 475, 9: 486, 10: 497,
    },
    "1급": {
        1: 462, 2: 474, 3: 486, 4: 498, 5: 510,
        6: 522, 7: 534, 8: 546, 9: 558, 10: 570,
    },
}

KWater_ALLOWANCES = {
    "직급보조비":  12.0,
    "식대":        14.0,
    "교통비":       7.0,
    "가족수당":     3.5,
    "복지포인트":   4.5,
}
KWater_ALLOWANCE_RATIOS = {
    "명절상여":   2.0,   # 기본급 × 200%/년
    "성과급":     2.5,   # 기본급 × 250%/년 (한전보다 성과급 낮음)
}


def make_kwater_fixture() -> ParsedSalaryTable:
    rows = [
        HobongRow(grade=grade, hobong=hobong, base_salary=base)
        for grade, hobong_dict in KWater_HOBONG.items()
        for hobong, base in hobong_dict.items()
    ]
    return ParsedSalaryTable(
        company_name="한국수자원공사",
        source_file="fixture:kwater_bosugyu_2024",
        hobong_rows=rows,
        allowances=KWater_ALLOWANCES,
        allowance_ratios=KWater_ALLOWANCE_RATIOS,
        parse_quality=0.95,
    )


# ─────────────────────────────────────────────────────────────

def print_table(company: str, parsed: ParsedSalaryTable):
    print(f"\n{'═'*72}")
    print(f"  {company}  연차별 연봉 (보수규정 기반, 2024년 기준)")
    print(f"  호봉 {len(parsed.hobong_rows)}개  |  수당 {len(parsed.allowances)}개  "
          f"|  신뢰도 {parsed.parse_quality:.0%}")
    print(f"{'─'*72}")

    points = build_career_table(parsed)
    table = format_career_table(points)

    print(f"  {'연차':6s}  {'직급':4s}  {'호봉':5s}  {'기본급':7s}  "
          f"{'세전연봉':9s}  {'월세전':7s}  {'실수령':7s}  {'공제율':5s}")
    print(f"  {'─'*6}  {'─'*4}  {'─'*5}  {'─'*7}  {'─'*9}  {'─'*7}  {'─'*7}  {'─'*5}")
    for row in table:
        print(f"  {row['연차']:6s}  {row['직급']:4s}  {row['호봉']:5s}  "
              f"{row['기본급']:7s}  {row['세전연봉']:9s}  "
              f"{row['월세전']:7s}  {row['실수령']:7s}  {row['공제율']:5s}")

    # 수당 구성 (6급 1호봉 기준 예시)
    base_6g_1h = next((r.base_salary for r in parsed.hobong_rows
                       if r.grade == "6급" and r.hobong == 1), 215)
    print(f"\n  [수당 구성 — 6급 1호봉 기본급 {base_6g_1h}만 기준]")
    for name, val in sorted(parsed.allowances.items(), key=lambda x: -x[1]):
        print(f"    {name:10s}  {val:6.1f}만/월  [고정]")
    for name, ratio in sorted(parsed.allowance_ratios.items(), key=lambda x: -x[1]):
        monthly_est = base_6g_1h * ratio / 12
        print(f"    {name:10s}  {monthly_est:6.1f}만/월  [기본급×{ratio:.0f}배/년]")

    total_fixed = sum(parsed.allowances.values())
    total_var_est = sum(base_6g_1h * r / 12 for r in parsed.allowance_ratios.values())
    ratio_total = sum(parsed.allowance_ratios.values())
    print(f"    {'─'*38}")
    print(f"    고정수당 합계   {total_fixed:6.1f}만/월")
    print(f"    변동수당 합계   {total_var_est:6.1f}만/월  (기본급×{ratio_total:.0f}배/년, 성과 따라 달라짐)")


def compare_with_old_estimate(company: str, parsed: ParsedSalaryTable, avg_salary: int, avg_tenure: float):
    """호봉 기반 vs 기존 평균 추정 방식 비교"""
    from src.processors.salary_analyzer import estimate_career_salary, format_salary_table

    print(f"\n{'─'*72}")
    print(f"  [방식 비교] {company}")
    print(f"  알리오 평균연봉 {avg_salary:,}만원 / 평균근속 {avg_tenure}년 기준")
    print(f"{'─'*72}")
    print(f"  {'연차':6s}  {'[A]호봉기반 실수령':>12s}  {'[B]추정방식 실수령':>12s}  {'차이':>8s}")
    print(f"  {'─'*6}  {'─'*12}  {'─'*12}  {'─'*8}")

    hobong_points = {p.career_year: p for p in build_career_table(parsed)}
    old_points = estimate_career_salary(avg_salary, avg_tenure)
    old_map = {p.year: p for p in old_points}

    for year in [1, 3, 5, 7, 10, 12, 15, 17, 20]:
        a = hobong_points.get(year)
        b = old_map.get(year)
        if not a or not b:
            continue
        diff = a.monthly_net_10k - b.monthly_net_10k
        diff_str = f"+{diff:.0f}만" if diff > 0 else f"{diff:.0f}만"
        print(f"  {year}년차    {a.monthly_net_10k:>10.0f}만    {b.monthly_net_10k:>10.0f}만  {diff_str:>8s}")


def main():
    # 한전
    kepco = make_kepco_fixture()
    print_table("한국전력공사", kepco)
    compare_with_old_estimate("한국전력공사", kepco, avg_salary=9100, avg_tenure=16.5)

    # 수공
    kwater = make_kwater_fixture()
    print_table("한국수자원공사", kwater)
    compare_with_old_estimate("한국수자원공사", kwater, avg_salary=8350, avg_tenure=14.2)


if __name__ == "__main__":
    main()
