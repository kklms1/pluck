"""
유튜브 발행 메타데이터 생성기
- SEO 제목 후보 (실수령/연봉 키워드 + 호기심 갭)
- 설명란 (챕터 타임스탬프 + 자소서/문제집 CTA 링크 + 출처 고지)
- 태그 / 해시태그
- 썸네일 텍스트 (2~3단어 큰 글씨용)

업로드 자동화(YouTube Data API)는 별도 단계. 여기서는 발행 패키지(json)까지 생성한다.
"""

from __future__ import annotations

import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../../output/meta")

# 판매 링크 (실제 스토어 URL로 교체)
SELF_INTRO_URL = "https://example.com/jaso"      # 자기소개서 기출 분석 PDF
EXAM_BOOK_URL = "https://example.com/gichul"      # NCS+직무 기출변형 문제집


def _won(man: float) -> str:
    man = round(man)
    if man >= 10000:
        return f"{man/10000:.2f}억".replace(".00억", "억")
    return f"{man:,}만원"


def build_metadata(
    company_name: str,
    career_points: list,
    analysis: dict = None,
    blind: dict = None,
    chapter_durations: dict = None,   # {"hook":5.5, "profile":6, "salary":95, ...} 초
) -> dict:
    """발행 메타데이터 dict 생성"""
    analysis = analysis or {}

    def pts(p, key, d=0):
        return (p.get(key, d) if isinstance(p, dict) else getattr(p, key, d))

    points = list(career_points or [])
    first = points[0] if points else {}
    last = points[-1] if points else {}
    net1 = pts(first, "monthly_net_10k")
    gross1 = pts(first, "annual_gross_10k")
    gross_last = pts(last, "annual_gross_10k")

    # ── 제목 후보 (A/B 테스트용) ──────────────────────────────
    titles = [
        f"{company_name} 연봉 실화? 신입 실수령 {net1:.0f}만원, 30년차엔 {_won(gross_last)}",
        f"[{company_name}] 1년차부터 30년차까지 연봉·실수령 전부 공개 (호봉표 분석)",
        f"{company_name} 들어가면 평생 얼마 벌까? 연차별 실수령 완벽정리",
    ]

    # ── 챕터 타임스탬프 ───────────────────────────────────────
    chapters = _build_chapters(chapter_durations or {})

    # ── 설명란 ────────────────────────────────────────────────
    asset = analysis.get("asset_info", {}) or {}
    b = blind or analysis.get("blind") or {}
    desc_lines = [
        f"{company_name}의 입사부터 30년차까지 연차별 세전연봉과 월 실수령액을 "
        f"알리오 보수규정(호봉표) 기준으로 분석했습니다.",
        "",
        f"▪ 신입 세전연봉: {_won(gross1)} (월 실수령 약 {net1:.0f}만원)",
        f"▪ 30년차 세전연봉: {_won(gross_last)}",
    ]
    if asset.get("total_assets_100m"):
        desc_lines.append(f"▪ 자산총계: {asset['total_assets_100m']:,}억원")
    if b.get("overall"):
        desc_lines.append(f"▪ 블라인드 종합평점: {b['overall']:.1f} / 5.0")
    loc = analysis.get("location") or {}
    if loc.get("region"):
        moved = f"지방이전({loc.get('innovation_city','')})" if loc.get("relocated") else "현 위치 유지"
        desc_lines.append(f"▪ 본사: {loc['region']} ({moved}) · 근무형태: {loc.get('rotation','')}")

    desc_lines += [
        "",
        "─" * 20,
        "📌 합격에 진짜 필요한 자료",
        f"• 자기소개서 기출 분석 PDF → {SELF_INTRO_URL}",
        f"• NCS + 직무 기출변형 문제집 → {EXAM_BOOK_URL}",
        "",
        "⏱ 챕터",
    ] + chapters + [
        "",
        "─" * 20,
        "※ 본 영상의 수치는 공공기관 경영정보 공개시스템(알리오)의 "
        "보수규정·복리후생비 공시 및 블라인드 공개 평점을 기반으로 추정한 것이며, "
        "개인별 실제 수령액과 차이가 있을 수 있습니다.",
        "",
        "#공기업 #공기업연봉 #공기업취업 #" + company_name.replace(" ", ""),
    ]

    # ── 태그 ──────────────────────────────────────────────────
    tags = [
        company_name, f"{company_name} 연봉", f"{company_name} 실수령",
        f"{company_name} 채용", "공기업 연봉", "공기업 취업", "공기업 실수령액",
        "공기업 호봉", "공기업 자소서", "NCS", "공기업 준비", "취준",
        "연차별 연봉", "공공기관 연봉",
        "공기업 근무지", "혁신도시", "공기업 순환근무", "공기업 지방근무",
    ]

    # ── 썸네일 문구 ───────────────────────────────────────────
    thumbnail = {
        "headline": f"신입 실수령 {net1:.0f}만",
        "sub": f"30년차 {_won(gross_last)}",
        "badge": company_name,
    }

    meta = {
        "company": company_name,
        "titles": titles,
        "primary_title": titles[0],
        "description": "\n".join(desc_lines),
        "tags": tags,
        "thumbnail": thumbnail,
        "category": "Education",
        "visibility": "private",   # 검수 후 수동/자동 public 전환
    }
    return meta


def _build_chapters(durations: dict) -> list[str]:
    """씬별 길이(초) → 'mm:ss 챕터명' 라인"""
    order = [
        ("hook", "💰 연봉 미리보기"),
        ("profile", "🏢 회사 규모 & 블라인드 평점"),
        ("location", "📍 본사 위치 & 순환근무"),
        ("salary", "📊 1~30년차 연봉/실수령"),
        ("welfare", "🎁 복리후생"),
        ("benefit", "🌴 휴가·휴직·제도"),
        ("growth", "📈 커리어 전망"),
        ("cta", "📚 합격 자료"),
    ]
    lines = []
    t = 0.0
    for key, label in order:
        if key not in durations:
            continue
        lines.append(f"{_ts(t)} {label}")
        t += durations[key]
    if not lines:
        lines.append("00:00 시작")
    return lines


def _ts(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def write_metadata(meta: dict, out_dir: str = None) -> str:
    out_dir = out_dir or os.path.join(OUTPUT_DIR, meta["company"])
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "youtube_meta.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # 사람이 바로 복붙할 수 있는 txt도 같이
    txt = os.path.join(out_dir, "youtube_upload.txt")
    with open(txt, "w", encoding="utf-8") as f:
        f.write("【제목 후보】\n")
        for i, t in enumerate(meta["titles"], 1):
            f.write(f"{i}. {t}\n")
        f.write("\n【설명란】\n")
        f.write(meta["description"] + "\n")
        f.write("\n【태그】\n")
        f.write(", ".join(meta["tags"]) + "\n")
        f.write("\n【썸네일】\n")
        th = meta["thumbnail"]
        f.write(f"메인: {th['headline']}\n보조: {th['sub']}\n배지: {th['badge']}\n")

    logger.info(f"메타데이터 저장: {path}")
    return path
