"""
생성 파이프라인 오프라인 통합 테스트 (네트워크/ moviepy 불필요)

검증:
  보수규정 픽스처 → 호봉 연봉(1~30년 단조증가)
  → 카드(후킹/연차30/기업규모/근무지/복지/혜택)
  → 대본 + SRT + 유튜브 메타데이터
"""

import sys
from dataclasses import asdict

sys.path.insert(0, ".")

from test_regulations_fixture import make_kepco_fixture
from src.processors.salary_from_hobong import build_career_table
import main


def build_fixture_analysis():
    points = build_career_table(make_kepco_fixture(), max_years=30)
    career = [asdict(p) for p in points]
    analysis = {
        "career_points": career,
        "welfare": [{
            "total_per_person_10k": 250, "meal_10k": 168, "transport_10k": 96,
            "medical_10k": 40, "childcare_tuition_10k": 120, "housing_loan_10k": 80,
            "welfare_point_10k": 200,
        }],
        "training": [{"per_person_10k": 75, "overseas_expense_10k": 1200}],
        "leave": {
            "annual_leave_max": 23, "summer_leave_days": 5, "sick_paid_days": 60,
            "parental_leave_months": 24, "marriage_days": 5,
            "flexible_work": True, "remote_work": True,
            "overseas_training": True, "mba_support": True, "career_break": True,
        },
        "asset_info": {"total_assets_100m": 2400000, "asset_rank": 1, "revenue_100m": 880000},
    }
    blind = {"overall": 3.6, "salary_benefit": 4.1, "work_life": 3.8,
             "culture": 3.0, "review_count": 4200}
    return career, analysis, blind


def test():
    career, analysis, blind = build_fixture_analysis()

    # 1) 연봉 단조 증가
    vals = [c["annual_gross_10k"] for c in career]
    assert len(career) == 30, f"연차 카드 수 {len(career)} != 30"
    assert all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1)), "연봉 역전 발생"
    print(f"✔ 연차 30개 · 단조증가 OK (1년차 {vals[0]:,} → 30년차 {vals[-1]:,}만)")

    # 2) 생성 파이프라인 (영상 제외)
    out = main.generate("한국전력공사", analysis, blind, make_video_flag=False)

    assert out["card_sequences"]["salary"], "연차 카드 미생성"
    assert len(out["card_sequences"]["salary"]) == 30
    assert out["profile_card"], "기업규모 카드 미생성"
    assert out["location_card"], "근무지 카드 미생성"
    assert out["welfare_card"] and out["benefit_card"], "복지/혜택 카드 미생성"
    print("✔ 카드: 후킹1 · 연차30 · 기업규모 · 근무지 · 복지 · 혜택 OK")

    # 3) 대본/메타
    import os
    assert os.path.exists(out["script"]["txt"]), "대본 미생성"
    assert os.path.exists(out["script"]["srt"]), "SRT 미생성"
    assert os.path.exists(out["meta"]), "메타데이터 미생성"

    txt = open(out["script"]["txt"], encoding="utf-8").read()
    assert "[LOCATION]" in txt, "대본에 근무지 씬 누락"
    assert "지방이전" in txt or "혁신도시" in txt, "근무지 내레이션 누락"
    print(f"✔ 대본/SRT/메타 OK (약 {out['script']['duration']:.0f}초)")

    import json
    meta = json.load(open(out["meta"], encoding="utf-8"))
    assert "본사" in meta["description"], "메타 설명에 본사 위치 누락"
    assert any("근무지" in t for t in meta["tags"]), "근무지 태그 누락"
    print(f"✔ 메타 제목: {meta['primary_title']}")

    print("\n🎉 ALL PASS — 생성 파이프라인 정상")


if __name__ == "__main__":
    test()
