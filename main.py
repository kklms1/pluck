"""
공기업 연봉 딥다이브 — 단일 기업 영상 자동화 파이프라인 (v2)

데이터(알리오/블라인드) → 호봉 연봉 → 카드 → 대본/TTS → 영상 → 발행 메타

사용법:
  # 1) 데이터 수집(로컬·Playwright 필요) 후 전체 생성
  python main.py --company "한국전력공사"

  # 2) 이미 수집된 캐시(data/{기업}_analysis.json)로 생성만 (네트워크 불필요)
  python main.py --company "한국전력공사" --from-cache

  # 3) 영상 없이 카드/대본/메타만 (moviepy 불필요)
  python main.py --company "한국전력공사" --from-cache --no-video

  # 4) 지원 기업 코드 목록
  python main.py --list
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")

# 기업별 CI 브랜드 색상 (썸네일/카드 accent)
COMPANY_COLORS = {
    "한국전력공사":     (0, 91, 172),
    "한국수자원공사":   (0, 159, 227),
    "한국가스공사":     (0, 71, 157),
    "한국토지주택공사": (0, 122, 94),
    "한국도로공사":     (0, 138, 89),
    "한국철도공사":     (0, 90, 169),
    "인천국제공항공사": (0, 60, 130),
    "국민건강보험공단": (0, 110, 183),
}
DEFAULT_COLOR = (64, 156, 255)

# 영상 타임라인 기본값 (video_maker 기본값과 일치시켜 챕터 계산에 사용)
HOOK_DUR = 5.0
PROFILE_DUR = 6.0
CARD_DUR = 3.0
SECTION_DUR = 2.0
WELFARE_CARD_DUR = 4.0


def _first(x):
    if isinstance(x, list):
        return x[0] if x else {}
    return x or {}


def generate(company_name: str, analysis: dict, blind: dict = None,
             make_video_flag: bool = True) -> dict:
    """analysis dict → 카드 + 대본 + 메타 (+영상). 산출물 경로 반환."""
    from src.generators.card_maker import (
        make_card_sequence, make_company_profile_card,
        make_welfare_card, make_benefit_card, make_location_card,
    )
    from src.data.location import get_location_dict
    from src.generators.script_maker import (
        build_script, write_script_files, synthesize_tts,
    )
    from src.generators.youtube_meta import build_metadata, write_metadata

    color = COMPANY_COLORS.get(company_name, DEFAULT_COLOR)
    career_points = analysis.get("career_points", [])
    if not career_points:
        logger.error("career_points 없음 — 보수규정 파싱이 안 됐거나 캐시가 비어있습니다.")
        return {}

    welfare = _first(analysis.get("welfare"))
    training = _first(analysis.get("training"))
    leave = analysis.get("leave", {}) or {}
    asset = analysis.get("asset_info", {}) or {}
    b = blind or analysis.get("blind") or {}

    # 근무지 정보: 캐시에 없으면 큐레이션 데이터로 보강
    location = analysis.get("location") or get_location_dict(company_name)
    analysis["location"] = location  # 대본/메타가 참조

    out = {}

    # ── 카드 시퀀스 (후킹 + 1~30년 + 섹션) ───────────────────
    logger.info("① 카드 시퀀스 생성...")
    seq = make_card_sequence(company_name, career_points, color)
    out["card_sequences"] = seq
    logger.info(f"   후킹 1 · 연차 {len(seq['salary'])} · 섹션 {len(seq['sections'])}")

    # ── 기업 규모 + 블라인드 카드 ─────────────────────────────
    logger.info("② 기업규모/블라인드 카드...")
    profile = make_company_profile_card(
        company_name,
        total_assets_100m=asset.get("total_assets_100m", 0),
        asset_rank=asset.get("asset_rank", 0),
        revenue_100m=asset.get("revenue_100m", 0),
        blind_overall=b.get("overall", 0),
        blind_salary=b.get("salary_benefit", 0),
        blind_worklife=b.get("work_life", 0),
        blind_culture=b.get("culture", 0),
        blind_review_count=b.get("review_count", 0),
        blind_screenshot_path=b.get("screenshot_path", ""),
        company_color=color,
    )
    out["profile_card"] = profile

    # ── 근무지 / 지방이전 / 순환근무 카드 ─────────────────────
    location_card = None
    if location:
        logger.info("②-b 근무지/순환근무 카드...")
        location_card = make_location_card(company_name, location, color)
        out["location_card"] = location_card

    # ── 복지 / 혜택 카드 ──────────────────────────────────────
    logger.info("③ 복지/혜택 카드...")
    welfare_card = make_welfare_card(company_name, welfare, training, color)
    benefit_card = make_benefit_card(company_name, leave, color)
    out["welfare_card"] = welfare_card
    out["benefit_card"] = benefit_card

    # ── 대본 + 자막 (+TTS) ────────────────────────────────────
    logger.info("④ 대본/자막 생성...")
    script = build_script(company_name, career_points, analysis, b)
    script_files = write_script_files(script)
    out["script"] = script_files
    logger.info(f"   대본 {len(script.lines)}줄 · 약 {script_files['duration']:.0f}초")

    narration = synthesize_tts(script)  # edge-tts 미설치/차단 시 None
    out["narration"] = narration
    if narration:
        import shutil, pathlib
        remotion_audio = pathlib.Path(__file__).parent / "remotion/public/narration.mp3"
        shutil.copy(narration, remotion_audio)
        logger.info(f"   내레이션 → Remotion: {remotion_audio}")

    # ── Remotion props.json 생성 ──────────────────────────────
    logger.info("④-b Remotion props.json 생성...")
    try:
        from src.generators.remotion_export import build_props, write_props, rgb_to_hex
        brand_hex = rgb_to_hex(color)
        props_dict = build_props(company_name, career_points, analysis, b or {}, brand_hex)
        props_path = write_props(props_dict)
        out["remotion_props"] = props_path
        logger.info(f"   props.json → {props_path}")
    except Exception as e:
        logger.warning(f"   remotion_export 실패: {e}")

    # ── 챕터 타임라인 → 메타데이터 ────────────────────────────
    logger.info("⑤ 유튜브 메타데이터...")
    chapter_durations = _chapter_durations(seq)
    meta = build_metadata(company_name, career_points, analysis, b, chapter_durations)
    meta_path = write_metadata(meta)
    out["meta"] = meta_path
    logger.info(f"   제목: {meta['primary_title']}")

    # ── 영상 조립 ─────────────────────────────────────────────
    if make_video_flag:
        logger.info("⑥ 영상 조립 (moviepy)...")
        try:
            from src.generators.video_maker import make_video
        except Exception as e:
            logger.warning(f"   moviepy 미사용 — 영상 생략: {e}")
            return out

        bgm = os.path.join("assets", "bgm", "epic_bgm.mp3")
        video = make_video(
            company_name=company_name,
            card_sequences=seq,
            profile_card_path=profile,
            location_card_path=location_card,
            welfare_card_paths=[welfare_card],
            benefit_card_paths=[benefit_card],
            bgm_path=bgm if os.path.exists(bgm) else None,
            narration_path=narration,
        )
        out["video"] = video
        if video:
            logger.info(f"   영상: {video}")
    else:
        logger.info("⑥ 영상 생략 (--no-video)")

    return out


def _chapter_durations(seq: dict) -> dict:
    """video_maker 타임라인 기준 씬별 길이(초) — 유튜브 챕터용"""
    n_salary = len(seq.get("salary", []))
    # 마일스톤(5의 배수)은 +0.5초
    salary_total = sum(CARD_DUR + (0.5 if (i + 1) % 5 == 0 else 0)
                       for i in range(n_salary))
    return {
        "hook":    len(seq.get("hook", [])) * HOOK_DUR + 0.5,
        "profile": PROFILE_DUR + 0.4,
        "location": PROFILE_DUR + 0.4,
        "salary":  salary_total + 0.3,
        "welfare": SECTION_DUR + WELFARE_CARD_DUR + 0.5,
        "benefit": SECTION_DUR + WELFARE_CARD_DUR + 0.5,
        "growth":  SECTION_DUR + 0.5,
        "cta":     5.0 + 0.5,
    }


def run_pipeline(company_name: str, inst_code: str, apba_id: str,
                 from_cache: bool, make_video_flag: bool,
                 headless: bool = True, fetch_blind: bool = False):
    logger.info(f"=== [{company_name}] 파이프라인 시작 ===")

    cache_path = Path("data") / f"{company_name}_analysis.json"

    # ── 데이터 확보: 캐시 or 신규 크롤링 ──────────────────────
    if from_cache:
        if not cache_path.exists():
            logger.error(f"캐시 없음: {cache_path} — 먼저 크롤링하세요.")
            return
        analysis = json.loads(cache_path.read_text(encoding="utf-8"))
        logger.info(f"캐시 로드: {cache_path}")
    else:
        import crawl_company
        analysis = crawl_company.run(
            company_name=company_name, inst_code=inst_code, apba_id=apba_id,
            headless=headless,
        )

    # ── 블라인드 평점 (선택) ──────────────────────────────────
    blind = analysis.get("blind")
    if fetch_blind and not blind:
        try:
            from src.crawlers.blind import get_rating
            blind = get_rating(company_name, headless=headless)
            if blind:
                analysis["blind"] = blind
                cache_path.write_text(
                    json.dumps(analysis, ensure_ascii=False, indent=2),
                    encoding="utf-8")
        except Exception as e:
            logger.warning(f"블라인드 수집 실패: {e}")

    # ── 생성 ──────────────────────────────────────────────────
    out = generate(company_name, analysis, blind, make_video_flag)

    logger.info(f"=== [{company_name}] 완료 ===")
    if out.get("meta"):
        print(f"\n  발행 패키지: output/meta/{company_name}/youtube_upload.txt")
    return out


def main():
    # 코드 사전은 crawl_company와 공유
    import crawl_company

    parser = argparse.ArgumentParser(description="공기업 연봉 딥다이브 자동화 파이프라인")
    parser.add_argument("--company", "-c", help="기업명 (예: 한국전력공사)")
    parser.add_argument("--inst-code", help="알리오 경영공시 기관코드")
    parser.add_argument("--apba-id", help="알리오 내부공시 apbaId")
    parser.add_argument("--from-cache", action="store_true",
                        help="data/{기업}_analysis.json 으로 생성만 (크롤링 생략)")
    parser.add_argument("--no-video", action="store_true", help="영상 생략 (카드/대본/메타만)")
    parser.add_argument("--blind", action="store_true", help="블라인드 평점 수집 시도")
    parser.add_argument("--show", action="store_true", help="브라우저 표시 (비헤드리스)")
    parser.add_argument("--list", action="store_true", help="지원 기업 목록")
    args = parser.parse_args()

    if args.list:
        print("\n지원 기업:")
        for name, codes in crawl_company.COMPANY_CODES.items():
            print(f"  {name:15s}  inst={codes['inst_code']}  apba={codes['apba_id']}")
        return

    if not args.company:
        parser.print_help()
        return

    codes = crawl_company.COMPANY_CODES.get(args.company, {})
    inst_code = args.inst_code or codes.get("inst_code", "")
    apba_id = args.apba_id or codes.get("apba_id", "")

    if not args.from_cache and not inst_code:
        print(f"⚠ '{args.company}'의 inst_code를 모릅니다. --list 확인 또는 --from-cache 사용")
        sys.exit(1)

    run_pipeline(
        company_name=args.company,
        inst_code=inst_code, apba_id=apba_id,
        from_cache=args.from_cache,
        make_video_flag=not args.no_video,
        headless=not args.show,
        fetch_blind=args.blind,
    )


if __name__ == "__main__":
    main()
