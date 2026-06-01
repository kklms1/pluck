"""
카드 이미지 시퀀스 → 유튜브 영상 조립기 (v2)

씬 구성 (단일 기업 딥다이브):
  [인트로]    후킹 카드 (세전연봉 + 월 실수령)
  [기업규모]  자산총계/순위 + 블라인드 평점 카드
  [섹션1]     연차별 연봉 카드 1~30년
  [섹션2]     복지·수당 섹션 카드 → 복지 카드
  [섹션3]     숨겨진 혜택 섹션 카드 → 혜택 카드
  [아웃트로]  CTA — 자소서·기출문제 판매
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "../../assets")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../../output/videos")


def make_video(
    company_name: str,
    card_sequences: dict,          # make_card_sequence() 반환값
    profile_card_path: Optional[str] = None,  # 기업규모/블라인드 카드
    welfare_card_paths: list[str] = None,
    benefit_card_paths: list[str] = None,
    bgm_path: Optional[str] = None,
    hook_duration: float = 5.0,    # 후킹 카드 표시 시간
    profile_duration: float = 6.0, # 기업 규모 카드 표시 시간
    card_duration: float = 3.0,    # 연차 카드 1장 시간 (30장 × 3초 = 90초)
    section_duration: float = 2.0,
    output_path: Optional[str] = None,
) -> Optional[str]:
    try:
        from moviepy.editor import (
            ImageClip, concatenate_videoclips, AudioFileClip,
            ColorClip, CompositeVideoClip,
        )
        from moviepy.video.fx.fadein import fadein
        from moviepy.video.fx.fadeout import fadeout
    except ImportError:
        logger.error("moviepy 미설치: pip install moviepy")
        return None

    clips = []

    def add_image(path: str, duration: float, fade_in: bool = False, fade_out: bool = False):
        if not path or not os.path.exists(path):
            logger.warning(f"이미지 없음: {path}")
            return
        c = ImageClip(path, duration=duration)
        if fade_in:
            c = fadein(c, 0.4)
        if fade_out:
            c = fadeout(c, 0.4)
        clips.append(c)

    def add_black(duration: float = 0.3):
        clips.append(ColorClip(size=(1920, 1080),
                               color=(0, 0, 0), duration=duration))

    # ── [인트로] 후킹 카드 ──────────────────────────────
    add_black(0.5)
    for p in card_sequences.get("hook", []):
        add_image(p, hook_duration, fade_in=True)

    # ── [기업 규모] 자산/순위/블라인드 평점 카드 ──────────
    if profile_card_path:
        add_black(0.4)
        add_image(profile_card_path, profile_duration, fade_in=True)

    # ── [섹션1] 연차별 연봉 카드 1~30년차 ───────────────
    add_black(0.3)
    salary_paths = card_sequences.get("salary", [])
    for i, p in enumerate(salary_paths):
        is_last = (i == len(salary_paths) - 1)
        # 마일스톤(5의 배수)은 0.5초 더 표시
        is_milestone = ((i + 1) % 5 == 0)
        dur = card_duration + (0.5 if is_milestone else 0)
        add_image(p, dur, fade_out=is_last)

    # ── [섹션2] 복지·수당 ────────────────────────────────
    sections = card_sequences.get("sections", [])
    welfare_section = next((p for p in sections if "복지" in p or "수당" in p), None)
    if welfare_section:
        add_black(0.5)
        add_image(welfare_section, section_duration, fade_in=True)
        for p in (welfare_card_paths or []):
            add_image(p, 4.0)

    # ── [섹션3] 숨겨진 혜택 ─────────────────────────────
    benefit_section = next((p for p in sections if "혜택" in p or "숨겨진" in p), None)
    if benefit_section:
        add_black(0.5)
        add_image(benefit_section, section_duration, fade_in=True)
        for p in (benefit_card_paths or []):
            add_image(p, 4.0)

    # ── [성장 가능성 섹션] ────────────────────────────────
    growth_section = next((p for p in sections if "성장" in p), None)
    if growth_section:
        add_black(0.5)
        add_image(growth_section, section_duration, fade_in=True)

    # ── [아웃트로] CTA ────────────────────────────────────
    add_black(0.5)
    outro = _make_outro_clip(company_name)
    clips.append(outro)

    if not clips:
        logger.error("클립 없음")
        return None

    final = concatenate_videoclips(clips, method="compose")

    # BGM
    if bgm_path and os.path.exists(bgm_path):
        try:
            audio = AudioFileClip(bgm_path).subclip(0, final.duration)
            audio = audio.audio_fadeout(3)
            final = final.set_audio(audio)
        except Exception as e:
            logger.warning(f"BGM 실패: {e}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not output_path:
        output_path = os.path.join(OUTPUT_DIR, f"{company_name}_딥다이브.mp4")

    final.write_videofile(
        output_path, fps=30,
        codec="libx264", audio_codec="aac",
        bitrate="8000k", verbose=False, logger=None,
    )
    logger.info(f"영상 완성: {output_path}")
    return output_path


def _make_outro_clip(company_name: str):
    """
    CTA 아웃트로 — 단일 기업 딥다이브 컨셉
    "합격하고 싶다면" → 자소서 + 기출 판매 연결
    비교 콘텐츠가 아닌 이 기업 전문 콘텐츠임을 강조
    """
    try:
        from moviepy.editor import ColorClip, TextClip, CompositeVideoClip
        bg = ColorClip(size=(1920, 1080), color=(12, 15, 25), duration=5)

        lines = [
            (f"{company_name}  합격의 모든 것", 80, "white",   340),
            ("자기소개서 기출 분석 PDF",          56, "#40c87c", 460),
            ("NCS + 직무 기출변형 문제집",         56, "#40c87c", 530),
            ("▶ 영상 설명란 링크에서 바로 확인",  44, "#9ca3b0", 630),
            ("구독하면 다음 기업 딥다이브도 알림", 36, "#6b7280", 720),
        ]

        text_clips = []
        for text, size, color, y in lines:
            tc = TextClip(text, fontsize=size, color=color,
                          font="NanumGothic-Bold" if size >= 56 else "NanumGothic",
                          size=(1700, None)
                          ).set_position(("center", y)).set_duration(5)
            text_clips.append(tc)

        return CompositeVideoClip([bg] + text_clips)
    except Exception:
        from moviepy.editor import ColorClip
        return ColorClip(size=(1920, 1080), color=(12, 15, 25), duration=5)
