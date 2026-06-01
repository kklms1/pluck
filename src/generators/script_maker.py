"""
무인(faceless) 영상 대본 · 내레이션 · 자막(SRT) 생성기

씬 순서(영상과 동일):
  [후킹] → [기업규모/블라인드] → [연차별 1~30년] → [복지] → [혜택] → [성장] → [CTA]

설계 원칙
  - 연차 카드는 30장이지만 내레이션은 마일스톤(1·5·10·15·20·25·30년차)만 짚어
    정보 밀도와 호흡을 유지한다 (전부 읽으면 늘어짐).
  - 모든 수치는 analysis dict에서 동적으로 채운다. 데이터가 없으면 해당 줄을 건너뛴다.
  - TTS(edge-tts)는 선택. 미설치/네트워크 차단 시에도 대본/SRT는 항상 생성된다.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../../output/scripts")

MILESTONE_YEARS = [1, 5, 10, 15, 20, 25, 30]


@dataclass
class ScriptLine:
    scene: str          # 씬 식별자 (hook/profile/salary/welfare/benefit/growth/cta)
    text: str           # 내레이션 문장
    duration: float     # 예상 노출/발화 시간(초)


@dataclass
class VideoScript:
    company_name: str
    lines: list[ScriptLine] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n".join(l.text for l in self.lines)

    @property
    def total_duration(self) -> float:
        return sum(l.duration for l in self.lines)


def _won(man: float) -> str:
    """만원 단위를 '천얼마/억' 자연어로 — 후킹용 가독성"""
    man = round(man)
    if man >= 10000:
        eok = man / 10000
        return f"{eok:.2f}억원".replace(".00억", "억")
    return f"{man:,}만원"


def _estimate_duration(text: str) -> float:
    """한국어 TTS 발화 시간 추정 (분당 약 330자 → 초당 5.5자), 최소 1.8초"""
    chars = len(text.replace(" ", ""))
    return max(1.8, round(chars / 5.5, 1))


def build_script(
    company_name: str,
    career_points: list,          # CareerPoint 객체/딕셔너리 리스트 (raw 수치)
    analysis: dict = None,        # welfare/training/leave/asset_info/blind 포함
    blind: dict = None,           # 블라인드 평점 dict (선택)
) -> VideoScript:
    """analysis 데이터 → 씬별 내레이션 대본"""
    analysis = analysis or {}
    script = VideoScript(company_name=company_name)

    def pts(p, key, default=0):
        return (p.get(key, default) if isinstance(p, dict) else getattr(p, key, default))

    points = list(career_points or [])
    by_year = {pts(p, "career_year"): p for p in points}

    # ── 1. 후킹 ──────────────────────────────────────────────
    if points:
        first = points[0]
        last = points[-1]
        net1 = pts(first, "monthly_net_10k")
        gross1 = pts(first, "annual_gross_10k")
        gross_last = pts(last, "annual_gross_10k")
        script.lines.append(ScriptLine(
            "hook",
            f"{company_name}, 신입 첫 달 실수령 {net1:.0f}만원. "
            f"세전 연봉으로는 {_won(gross1)}부터 시작합니다.",
            5.0,
        ))
        script.lines.append(ScriptLine(
            "hook",
            f"그리고 30년차가 되면 연봉은 {_won(gross_last)}까지 오릅니다. "
            f"오늘 입사부터 정년까지, 호봉표 그대로 전부 까보겠습니다.",
            4.5,
        ))

    # ── 2. 기업 규모 + 블라인드 ───────────────────────────────
    asset = analysis.get("asset_info", {}) or {}
    prof_bits = []
    if asset.get("total_assets_100m"):
        prof_bits.append(f"자산총계 {asset['total_assets_100m']:,}억원")
    if asset.get("asset_rank"):
        prof_bits.append(f"공공기관 자산순위 {asset['asset_rank']}위")
    if prof_bits:
        script.lines.append(ScriptLine(
            "profile",
            f"먼저 회사 체급부터. {', '.join(prof_bits)} 규모의 기관입니다.",
            5.0,
        ))
    b = blind or analysis.get("blind") or {}
    if b.get("overall"):
        script.lines.append(ScriptLine(
            "profile",
            f"실제 다니는 사람들의 평가, 블라인드 종합 평점은 5점 만점에 "
            f"{b['overall']:.1f}점. 급여·복지 {b.get('salary_benefit',0):.1f}점, "
            f"워라밸 {b.get('work_life',0):.1f}점입니다.",
            5.0,
        ))

    # ── 2-b. 근무지 / 지방이전 / 순환근무 ─────────────────────
    loc = analysis.get("location") or {}
    if loc.get("region"):
        moved = (f"{loc.get('innovation_city','')}로 지방이전한"
                 if loc.get("relocated") else "현 위치를 유지하는")
        rotation = loc.get("rotation", "")
        rot_phrase = {
            "전국순환": "전국 사업소를 도는 순환근무라 이사 각오는 필요합니다",
            "권역순환": "권역 안에서 순환근무가 이뤄집니다",
            "본사상주": "한 사업장에 상주해 이사 부담은 적은 편입니다",
        }.get(rotation, "")
        line = (f"근무지도 중요하죠. 본사는 {loc['region']}, "
                f"{moved} 기관입니다. {rot_phrase}.")
        script.lines.append(ScriptLine("location", line, _estimate_duration(line)))

    # ── 3. 연차별 (마일스톤만) ────────────────────────────────
    for yr in MILESTONE_YEARS:
        p = by_year.get(yr)
        if not p:
            continue
        grade = pts(p, "grade")
        gross = pts(p, "annual_gross_10k")
        net = pts(p, "monthly_net_10k")
        if yr == 1:
            line = (f"1년차. {grade}, 세전 {_won(gross)}, "
                    f"매달 통장에 {net:.0f}만원이 찍힙니다.")
        elif yr == 30:
            line = (f"그리고 30년차. {grade}까지 올라가면 세전 {_won(gross)}, "
                    f"월 실수령 {net:.0f}만원. 여기가 사실상 천장입니다.")
        else:
            line = (f"{yr}년차, {grade}. 세전 {_won(gross)}, "
                    f"실수령은 월 {net:.0f}만원으로 올라옵니다.")
        script.lines.append(ScriptLine("salary", line, _estimate_duration(line)))

    # ── 4. 복지 ──────────────────────────────────────────────
    welfare = (analysis.get("welfare") or [{}])
    welfare = welfare[0] if isinstance(welfare, list) else welfare
    total_w = welfare.get("total_per_person_10k", 0)
    if total_w:
        script.lines.append(ScriptLine(
            "welfare",
            f"연봉이 다가 아닙니다. 1인당 복리후생비만 연 {total_w:,.0f}만원. "
            f"식대, 의료비, 학자금, 복지포인트가 여기에 더해집니다.",
            5.0,
        ))

    # ── 5. 숨겨진 혜택 (휴가/제도) ────────────────────────────
    leave = analysis.get("leave") or {}
    flag_names = {
        "flexible_work": "유연근무", "remote_work": "재택근무",
        "overseas_training": "해외연수", "mba_support": "MBA 지원",
        "career_break": "리프레시 휴직",
    }
    active = [name for key, name in flag_names.items() if leave.get(key)]
    if leave.get("parental_leave_months") or active:
        bits = []
        if leave.get("annual_leave_max"):
            bits.append(f"연차 최대 {leave['annual_leave_max']}일")
        if leave.get("parental_leave_months"):
            bits.append(f"육아휴직 {leave['parental_leave_months']}개월")
        if active:
            bits.append(" · ".join(active))
        script.lines.append(ScriptLine(
            "benefit",
            f"진짜 꿀은 여기. {', '.join(bits)}까지. "
            f"채용공고엔 잘 안 적히는 부분입니다.",
            5.0,
        ))

    # ── 6. 성장 가능성 ────────────────────────────────────────
    if points:
        script.lines.append(ScriptLine(
            "growth",
            "정리하면, 시작은 평범해 보여도 호봉이 쌓일수록 격차가 벌어집니다. "
            "문제는 '들어갈 수 있느냐'겠죠.",
            4.5,
        ))

    # ── 7. CTA ───────────────────────────────────────────────
    script.lines.append(ScriptLine(
        "cta",
        f"{company_name} 합격에 진짜 필요한 자기소개서 기출 분석과 "
        f"직무 기출변형 문제집은 영상 설명란 링크에 정리해 뒀습니다. "
        f"구독하면 다음 기업 딥다이브도 놓치지 않습니다.",
        6.0,
    ))

    return script


def write_script_files(script: VideoScript, out_dir: str = None) -> dict:
    """대본(.txt) + 자막(.srt) 저장. 경로 dict 반환."""
    out_dir = out_dir or os.path.join(OUTPUT_DIR, script.company_name)
    os.makedirs(out_dir, exist_ok=True)

    txt_path = os.path.join(out_dir, "narration.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"# {script.company_name} 연봉 딥다이브 내레이션\n")
        f.write(f"# 예상 분량: 약 {script.total_duration:.0f}초 "
                f"({script.total_duration/60:.1f}분)\n\n")
        cur = None
        for l in script.lines:
            if l.scene != cur:
                f.write(f"\n[{l.scene.upper()}]\n")
                cur = l.scene
            f.write(l.text + "\n")

    srt_path = os.path.join(out_dir, "narration.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        t = 0.0
        for i, l in enumerate(script.lines, 1):
            start, end = t, t + l.duration
            f.write(f"{i}\n{_srt_ts(start)} --> {_srt_ts(end)}\n{l.text}\n\n")
            t = end

    logger.info(f"대본 저장: {txt_path}")
    return {"txt": txt_path, "srt": srt_path, "duration": script.total_duration}


def _srt_ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def synthesize_tts(
    script: VideoScript,
    out_path: str = None,
    voice: str = "ko-KR-InJoonNeural",
) -> Optional[str]:
    """
    edge-tts로 전체 내레이션을 mp3로 합성 (선택 기능).
    미설치/네트워크 차단 시 None 반환 — 파이프라인은 무음 BGM으로 진행.

    설치: pip install edge-tts
    """
    try:
        import asyncio
        import edge_tts
    except ImportError:
        logger.warning("edge-tts 미설치 — TTS 건너뜀 (pip install edge-tts)")
        return None

    out_path = out_path or os.path.join(
        OUTPUT_DIR, script.company_name, "narration.mp3")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    text = "  ".join(l.text for l in script.lines)

    async def _run():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(out_path)

    try:
        asyncio.run(_run())
        logger.info(f"TTS 저장: {out_path}")
        return out_path
    except Exception as e:
        logger.warning(f"TTS 합성 실패: {e}")
        return None
