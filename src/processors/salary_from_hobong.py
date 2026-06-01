"""
호봉 테이블 기반 정확한 연봉 계산
- 호봉 기본급 + 수당 → 세전 연봉
- 연차별 호봉 매핑 (대졸 공채 기준: 1년 = 1호봉)
- 실수령액 계산 연동
"""

from dataclasses import dataclass, field
from typing import Optional
import logging

from .regulation_parser import ParsedSalaryTable, HobongRow
from .salary_analyzer import calc_monthly_net, YearlySalary

logger = logging.getLogger(__name__)


# 대졸 공채 신입 초봉 호봉 (기관별로 다르나 일반적으로 1~3호봉)
DEFAULT_START_HOBONG = {
    "6급": 1,   # 신입 1호봉 시작
}

# 연차별 직급 이동 패턴 (일반 공기업 대졸 공채, 30년까지)
# (최소 연차, 직급)
CAREER_GRADE_MAP = [
    (1,  "6급"),
    (3,  "5급"),
    (7,  "4급"),
    (12, "3급"),
    (17, "2급"),
    (22, "1급"),
    (27, "부장/처장급"),
]


@dataclass
class CareerPoint:
    career_year: int            # 입사 후 연차
    grade: str                  # 직급
    hobong: int                 # 호봉
    base_salary_10k: int        # 기본급 (만원)
    total_allowance_10k: float  # 수당 합계 (만원/월)
    annual_gross_10k: int       # 세전 연봉 (만원)
    monthly_gross_10k: float    # 월 세전 (만원)
    monthly_net_10k: float      # 월 실수령 (만원)
    tax_rate_pct: float


def build_career_table(
    parsed: ParsedSalaryTable,
    start_hobong: int = 1,
    max_years: int = 25,
) -> list[CareerPoint]:
    """
    호봉 테이블 + 수당 → 연차별 실수령 테이블

    연차 → 직급 → 호봉 → 기본급 조회 → 수당 합산 → 실수령 계산
    """
    # 호봉 테이블을 {직급: {호봉: 기본급}} dict로 변환
    hobong_map: dict[str, dict[int, int]] = {}
    for row in parsed.hobong_rows:
        hobong_map.setdefault(row.grade, {})[row.hobong] = row.base_salary

    if not hobong_map:
        logger.warning("호봉 테이블 비어있음 — 추정 모드로 전환")
        return []

    # 고정 수당 합계 (식대·교통비 등 절대 금액)
    fixed_monthly = sum(parsed.allowances.values())
    logger.info(f"  월 고정수당 합계: {fixed_monthly:.1f}만원")

    # 기본급 비례 수당 연간 배수 합계 (성과급 3.0 + 명절상여 2.0 = 5.0)
    ratio_total = sum(parsed.allowance_ratios.values())
    if not ratio_total:
        # allowance_ratios 없으면 공기업 평균 기준 추정 (연간 기본급 × 500%)
        ratio_total = 5.0
        logger.info(f"  비례수당 배수 없음 → 공기업 평균 {ratio_total}배 적용")
    else:
        logger.info(f"  비례수당 연간 배수: {ratio_total:.1f}배 "
                    f"({dict(parsed.allowance_ratios)})")

    results = []
    for career_year in _key_years(max_years):
        grade = _grade_for_year(career_year)
        hobong = start_hobong + career_year - 1

        grade_table = hobong_map.get(grade, {})
        if not grade_table:
            grade_table = _fallback_grade(hobong_map, grade)

        base = _lookup_hobong(grade_table, hobong)
        if base == 0:
            logger.debug(f"  {career_year}년차 {grade} {hobong}호봉: 기본급 없음")
            continue

        # 기본급 비례 수당 월 환산: base × 연간배수 / 12
        ratio_monthly = base * ratio_total / 12
        total_monthly = base + fixed_monthly + ratio_monthly

        annual_gross = round(total_monthly * 12 / 100) * 100
        net_info = calc_monthly_net(annual_gross)

        results.append(CareerPoint(
            career_year=career_year,
            grade=grade,
            hobong=hobong,
            base_salary_10k=base,
            total_allowance_10k=fixed_monthly + ratio_monthly,
            annual_gross_10k=annual_gross,
            monthly_gross_10k=net_info["monthly_gross_10k"],
            monthly_net_10k=net_info["monthly_net_10k"],
            tax_rate_pct=net_info["tax_rate_pct"],
        ))

    return results


def _grade_for_year(career_year: int) -> str:
    grade = "6급"
    for min_year, g in CAREER_GRADE_MAP:
        if career_year >= min_year:
            grade = g
    return grade


def _lookup_hobong(grade_table: dict[int, int], hobong: int) -> int:
    """호봉 조회 (없으면 가장 가까운 호봉으로 대체)"""
    if hobong in grade_table:
        return grade_table[hobong]
    if not grade_table:
        return 0
    # 가장 가까운 호봉
    closest = min(grade_table.keys(), key=lambda k: abs(k - hobong))
    return grade_table[closest]


def _fallback_grade(hobong_map: dict, target_grade: str) -> dict:
    """직급 없을 때 숫자 순으로 인접 직급 탐색"""
    grade_order = ["6급", "5급", "4급", "3급", "2급", "1급"]
    idx = grade_order.index(target_grade) if target_grade in grade_order else -1
    for offset in [1, -1, 2, -2]:
        adj_idx = idx + offset
        if 0 <= adj_idx < len(grade_order):
            adj = grade_order[adj_idx]
            if adj in hobong_map:
                return hobong_map[adj]
    return {}


def _key_years(max_years: int) -> list[int]:
    """1년차부터 max_years까지 1년 단위 전체 목록"""
    return list(range(1, max_years + 1))


def format_career_table(points: list[CareerPoint]) -> list[dict]:
    return [
        {
            "연차":     f"{p.career_year}년차",
            "직급":     p.grade,
            "호봉":     f"{p.hobong}호봉",
            "기본급":   f"{p.base_salary_10k:,}만원",
            "세전연봉": f"{p.annual_gross_10k:,}만원",
            "월세전":   f"{p.monthly_gross_10k:.0f}만원",
            "실수령":   f"{p.monthly_net_10k:.0f}만원",
            "공제율":   f"{p.tax_rate_pct:.1f}%",
        }
        for p in points
    ]
