"""
연봉 데이터 처리 및 분석
- 연차별 추정 연봉 계산
- 실수령액 계산 (세금/4대보험 공제)
- 직급별 연봉 테이블 생성
"""

import math
from dataclasses import dataclass
from typing import Optional


# 2024년 기준 소득세 과세표준 (단위: 만원)
TAX_BRACKETS = [
    (1400, 0.06),
    (5000, 0.15),
    (8800, 0.24),
    (15000, 0.35),
    (30000, 0.38),
    (50000, 0.40),
    (100000, 0.42),
    (float("inf"), 0.45),
]

# 4대보험 요율 (2024년 기준, 근로자 부담분)
INSURANCE_RATES = {
    "국민연금": 0.045,
    "건강보험": 0.03545,
    "고용보험": 0.009,
    "장기요양": 0.03545 * 0.1295,  # 건강보험료의 12.95%
}


@dataclass
class YearlySalary:
    year: int                  # 입사 후 연차
    grade: str                 # 직급명
    annual_gross_10k: int      # 세전 연봉 (만원)
    monthly_gross_10k: float   # 세전 월급 (만원)
    monthly_net_10k: float     # 실수령액 (만원)
    tax_rate_pct: float        # 실효세율 (%)
    insurance_10k: float       # 월 4대보험 (만원)
    income_tax_10k: float      # 월 소득세+지방세 (만원)


def calc_income_tax(annual_gross_10k: int) -> float:
    """연봉 기준 연간 소득세 계산 (만원 단위 반환)"""
    # 근로소득공제
    if annual_gross_10k <= 500:
        deduction = annual_gross_10k * 0.70
    elif annual_gross_10k <= 1500:
        deduction = 350 + (annual_gross_10k - 500) * 0.40
    elif annual_gross_10k <= 4500:
        deduction = 750 + (annual_gross_10k - 1500) * 0.15
    elif annual_gross_10k <= 10000:
        deduction = 1200 + (annual_gross_10k - 4500) * 0.05
    else:
        deduction = 1475 + (annual_gross_10k - 10000) * 0.02
    deduction = min(deduction, 2000)

    # 인적공제 (본인 150만원)
    personal_deduction = 150

    taxable = max(0, annual_gross_10k - deduction - personal_deduction)

    tax = 0.0
    prev_limit = 0
    for limit, rate in TAX_BRACKETS:
        if taxable <= prev_limit:
            break
        taxable_in_bracket = min(taxable, limit) - prev_limit
        tax += taxable_in_bracket * rate
        prev_limit = limit

    # 지방소득세 10%
    tax *= 1.10
    return tax


def calc_monthly_net(annual_gross_10k: int) -> dict:
    """월 실수령액 계산"""
    monthly_gross = annual_gross_10k / 12

    # 4대보험 (월 기준)
    insurance = {
        name: monthly_gross * rate
        for name, rate in INSURANCE_RATES.items()
    }
    total_insurance = sum(insurance.values())

    # 소득세 (연간 → 월할)
    annual_tax = calc_income_tax(annual_gross_10k)
    monthly_tax = annual_tax / 12

    monthly_net = monthly_gross - total_insurance - monthly_tax

    return {
        "monthly_gross_10k": round(monthly_gross, 1),
        "monthly_net_10k": round(monthly_net, 1),
        "insurance_10k": round(total_insurance, 1),
        "income_tax_10k": round(monthly_tax, 1),
        "tax_rate_pct": round((total_insurance + monthly_tax) / monthly_gross * 100, 1),
        "insurance_breakdown": {k: round(v, 2) for k, v in insurance.items()},
    }


PUBLIC_CORP_GRADES = {
    "대졸 공채": [
        (1, "6급", 3200),
        (3, "5급", 3800),
        (6, "4급", 4600),
        (10, "3급", 5400),
        (15, "2급", 6200),
        (20, "1급", 7200),
        (25, "부장/처장급", 8000),
    ],
}


def estimate_career_salary(
    base_avg_salary_10k: int,
    avg_tenure_years: float,
    company_type: str = "대졸 공채",
) -> list[YearlySalary]:
    """
    알리오 평균연봉 + 평균근속연수를 기반으로
    연차별 연봉 추정 테이블 생성
    """
    grade_table = PUBLIC_CORP_GRADES.get(company_type, PUBLIC_CORP_GRADES["대졸 공채"])

    # 평균연봉을 기준점으로 스케일 조정
    # 평균근속연수에 해당하는 grade의 기준 연봉과 비교
    ref_year = avg_tenure_years
    ref_grade = _find_grade(grade_table, ref_year)
    scale = base_avg_salary_10k / ref_grade[2] if ref_grade else 1.0

    results = []
    for year, grade_name, base in grade_table:
        adjusted = round(base * scale / 100) * 100  # 100만원 단위 반올림
        net_info = calc_monthly_net(adjusted)
        results.append(YearlySalary(
            year=year,
            grade=grade_name,
            annual_gross_10k=adjusted,
            monthly_gross_10k=net_info["monthly_gross_10k"],
            monthly_net_10k=net_info["monthly_net_10k"],
            insurance_10k=net_info["insurance_10k"],
            income_tax_10k=net_info["income_tax_10k"],
            tax_rate_pct=net_info["tax_rate_pct"],
        ))

    return results


def _find_grade(grade_table: list, target_year: float):
    for i in range(len(grade_table) - 1):
        if grade_table[i][0] <= target_year < grade_table[i + 1][0]:
            return grade_table[i]
    return grade_table[-1] if grade_table else None


def format_salary_table(salary_list: list[YearlySalary]) -> list[dict]:
    return [
        {
            "연차": f"{s.year}년차",
            "직급": s.grade,
            "세전연봉": f"{s.annual_gross_10k:,}만원",
            "월세전": f"{s.monthly_gross_10k:.0f}만원",
            "실수령액": f"{s.monthly_net_10k:.0f}만원",
            "공제율": f"{s.tax_rate_pct:.1f}%",
        }
        for s in salary_list
    ]
