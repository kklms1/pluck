"""
Python 파이프라인 → Remotion props.json 익스포터

Remotion(React)이 영상/썸네일을 렌더링할 때 읽는 단일 데이터 파일을 생성한다.
Python = 데이터/연봉/분석(brains), Remotion = 디자인/모션(looks) 의 분리.
"""

from __future__ import annotations

import json
import os
from typing import Optional

REMOTION_PUBLIC = os.path.join(os.path.dirname(__file__), "../../remotion/public")

DEFAULT_BRAND = "#3aa0ff"


def build_props(
    company_name: str,
    career_points: list,
    analysis: dict = None,
    blind: dict = None,
    brand_color_hex: str = DEFAULT_BRAND,
) -> dict:
    analysis = analysis or {}

    def g(p, k, d=0):
        return (p.get(k, d) if isinstance(p, dict) else getattr(p, k, d))

    career = [
        {
            "career_year": g(p, "career_year"),
            "grade": g(p, "grade", ""),
            "hobong": g(p, "hobong"),
            "annual_gross_10k": g(p, "annual_gross_10k"),
            "monthly_gross_10k": round(g(p, "monthly_gross_10k"), 1),
            "monthly_net_10k": round(g(p, "monthly_net_10k"), 1),
            "tax_rate_pct": round(g(p, "tax_rate_pct"), 1),
            "insurance_10k": round(g(p, "insurance_10k", 0), 1),
            "income_tax_10k": round(g(p, "income_tax_10k", 0), 1),
            # 항목별 명세 (만원/월)
            "base_salary_10k": g(p, "base_salary_10k"),
            "fixed_allow_10k": round(g(p, "fixed_allow_10k", 0), 1),
            "perform_allow_10k": round(g(p, "perform_allow_10k", 0), 1),
            "welfare_10k": round(g(p, "welfare_10k", 0), 1),
            "bonus_10k": round(g(p, "bonus_10k", 0), 1),
            "monthly_regular_net_10k": round(g(p, "monthly_regular_net_10k", 0), 1),
        }
        for p in (career_points or [])
    ]

    welfare = analysis.get("welfare")
    if isinstance(welfare, list):
        welfare = welfare[0] if welfare else {}

    return {
        "company": company_name,
        "brandColor": brand_color_hex,
        "career": career,
        "asset": analysis.get("asset_info", {}),
        "blind": blind or analysis.get("blind") or {},
        "location": analysis.get("location", {}),
        "welfare": {"total_per_person_10k": (welfare or {}).get("total_per_person_10k", 0)},
    }


def rgb_to_hex(rgb: tuple) -> str:
    return "#%02x%02x%02x" % (int(rgb[0]), int(rgb[1]), int(rgb[2]))


def write_props(props: dict, out_path: Optional[str] = None) -> str:
    out_path = out_path or os.path.join(REMOTION_PUBLIC, "props.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)
    return out_path
