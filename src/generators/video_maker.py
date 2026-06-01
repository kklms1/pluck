"""
카드 이미지 시퀀스 → 유튜브 영상 조립기
- 카드 넘기기 트랜지션
- BGM 삽입
- 인트로/아웃트로 CTA 화면
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "../../assets")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../../output/videos")


def make_video(
    company_name: str,
    card_image_paths: list[str],
    bgm_path: Optional[str] = None,
    card_duration: float = 4.0,
    transition_duration: float = 0.5,
    output_path: Optional[str] = None,
) -> Optional[str]:
    """
    카드 이미지 → 영상 합성
    card_duration: 카드 1장 표시 시간 (초)
    transition_duration: 전환 효과 시간 (초)
    """
    try:
        from moviepy.editor import (
            ImageClip, concatenate_videoclips, AudioFileClip,
            CompositeVideoClip, ColorClip, TextClip,
        )
        from moviepy.video.fx.fadein import fadein
        from moviepy.video.fx.fadeout import fadeout
    except ImportError:
        logger.error("moviepy 미설치: pip install moviepy")
        return None

    if not card_image_paths:
        logger.error("카드 이미지 없음")
        return None

    clips = []

    # 인트로 (0.5초 블랙 페이드인)
    intro = ColorClip(size=(1920, 1080), color=(0, 0, 0), duration=0.5)
    clips.append(intro)

    for i, img_path in enumerate(card_image_paths):
        if not os.path.exists(img_path):
            logger.warning(f"이미지 없음: {img_path}")
            continue

        clip = ImageClip(img_path, duration=card_duration)

        # 페이드 전환
        if i == 0:
            clip = fadein(clip, transition_duration)
        if i == len(card_image_paths) - 1:
            clip = fadeout(clip, transition_duration)

        clips.append(clip)

    if len(clips) <= 1:
        logger.error("유효한 클립 없음")
        return None

    # CTA 아웃트로 (3초)
    outro = _make_outro_clip(company_name)
    clips.append(outro)

    final = concatenate_videoclips(clips, method="compose")

    # BGM 삽입
    if bgm_path and os.path.exists(bgm_path):
        try:
            audio = AudioFileClip(bgm_path).subclip(0, final.duration)
            audio = audio.audio_fadeout(2)
            final = final.set_audio(audio)
        except Exception as e:
            logger.warning(f"BGM 삽입 실패: {e}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not output_path:
        output_path = os.path.join(OUTPUT_DIR, f"{company_name}_연봉공개.mp4")

    final.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        bitrate="8000k",
        verbose=False,
        logger=None,
    )

    logger.info(f"영상 생성 완료: {output_path}")
    return output_path


def _make_outro_clip(company_name: str):
    """CTA 아웃트로 클립 생성"""
    try:
        from moviepy.editor import ColorClip, TextClip, CompositeVideoClip
    except ImportError:
        from moviepy.editor import ColorClip
        return ColorClip(size=(1920, 1080), color=(12, 15, 25), duration=3)

    bg = ColorClip(size=(1920, 1080), color=(12, 15, 25), duration=3)

    try:
        title = TextClip(
            f"{company_name} 합격을 원한다면?",
            fontsize=72,
            color="white",
            font="NanumGothic-Bold",
            size=(1600, None),
        ).set_position(("center", 350)).set_duration(3)

        cta = TextClip(
            "▶ 자기소개서 + 기출변형문제 → 영상 설명란 링크",
            fontsize=48,
            color="#40c87c",
            font="NanumGothic",
        ).set_position(("center", 520)).set_duration(3)

        return CompositeVideoClip([bg, title, cta])
    except Exception:
        return bg
