"""
공기업 유튜브 자동화 파이프라인
사용법:
  python main.py --company "한국전력공사"
  python main.py --auto            # 공취사 최근 공고 기업 전체 자동화
  python main.py --list            # 처리 가능 기업 목록 확인
"""

import argparse
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.db import init_db, upsert_company, save_salary_records, save_career_salary
from src.db import save_evaluator_stat, log_video, get_latest_salary
from src.crawlers.allio import AllioCrawler
from src.crawlers.gongchwi import GongchwaCrawler
from src.crawlers.blind import BlindCrawler
from src.processors.salary_analyzer import estimate_career_salary, format_salary_table
from src.processors.evaluator_analyzer import analyze_evaluator_activity
from src.generators.card_maker import make_card_sequence
from src.generators.video_maker import make_video

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")


def run_pipeline(company_name: str, make_video_flag: bool = True):
    logger.info(f"=== [{company_name}] 파이프라인 시작 ===")

    # 1. 알리오 데이터 수집
    logger.info("① 알리오 연봉 데이터 수집...")
    allio = AllioCrawler()
    allio_data = allio.collect(company_name)
    inst_code = allio_data.get("inst_code")

    upsert_company(company_name, inst_code)

    if allio_data["salary"]:
        save_salary_records(allio_data["salary"])
        logger.info(f"   연봉 {len(allio_data['salary'])}건 저장")
    else:
        logger.warning("   알리오 데이터 없음 — 기본값으로 추정")

    # 2. 연차별 연봉 추정
    logger.info("② 연차별 연봉 테이블 생성...")
    latest = get_latest_salary(company_name)
    if latest:
        avg_salary = latest["avg_salary_10k"]
        avg_tenure = latest["avg_tenure_years"]
    else:
        avg_salary = 5000
        avg_tenure = 10.0

    career_salary = estimate_career_salary(avg_salary, avg_tenure)
    save_career_salary(company_name, career_salary)

    table = format_salary_table(career_salary)
    print(f"\n{'─'*60}")
    print(f"  {company_name} 연차별 연봉 추정")
    print(f"{'─'*60}")
    for row in table:
        print(f"  {row['연차']:6s} | {row['직급']:6s} | 연봉 {row['세전연봉']:10s} | 실수령 {row['실수령액']}")
    print(f"{'─'*60}\n")

    # 3. 평가위원 활동률 분석
    logger.info("③ 평가위원 활동률 분석...")
    eval_stat = analyze_evaluator_activity(company_name, inst_code)
    save_evaluator_stat(eval_stat)
    logger.info(f"   성장점수: {eval_stat.growth_score}/10 — {eval_stat.interpretation}")

    # 4. 블라인드 수집 (선택)
    logger.info("④ 블라인드 리뷰 수집 (Playwright 필요)...")
    blind = BlindCrawler()
    blind_result = blind.collect(company_name)
    if blind_result:
        from src.db import save_blind_summary
        save_blind_summary(blind_result)
        logger.info(f"   블라인드 평점: {blind_result['avg_rating']}, 리뷰 {blind_result['review_count']}건")
    else:
        logger.info("   블라인드 수집 건너뜀 (계정 or 설치 필요)")

    # 5. 카드 이미지 생성
    logger.info("⑤ 카드 이미지 생성...")
    card_paths = make_card_sequence(
        company_name=company_name,
        salary_list=[s.__dict__ for s in career_salary],
        company_color=(64, 156, 255),
    )
    logger.info(f"   카드 {len(card_paths)}장 생성")

    # 6. 영상 조립
    if make_video_flag and card_paths:
        logger.info("⑥ 영상 조립...")
        bgm_path = os.path.join("assets", "bgm", "epic_bgm.mp3")
        video_path = make_video(
            company_name=company_name,
            card_image_paths=card_paths,
            bgm_path=bgm_path if os.path.exists(bgm_path) else None,
        )
        if video_path:
            log_video(company_name, video_path, len(card_paths))
            logger.info(f"   영상 저장: {video_path}")
    else:
        logger.info("⑥ 영상 생성 건너뜀 (--no-video 옵션)")

    logger.info(f"=== [{company_name}] 완료 ===\n")


def run_auto_pipeline(pages: int = 3):
    """공취사 최근 공고 기업 자동 수집 후 파이프라인 실행"""
    logger.info("공취사 최근 채용공고 수집 중...")
    crawler = GongchwaCrawler()
    company_names = crawler.get_company_names(pages=pages)
    logger.info(f"수집된 기업: {len(company_names)}개")

    for name in company_names:
        try:
            run_pipeline(name, make_video_flag=False)
        except Exception as e:
            logger.error(f"{name} 파이프라인 실패: {e}")
            continue


def main():
    init_db()

    parser = argparse.ArgumentParser(description="공기업 유튜브 자동화 파이프라인")
    parser.add_argument("--company", "-c", type=str, help="기업명 (예: 한국전력공사)")
    parser.add_argument("--auto", "-a", action="store_true", help="공취사 최근 공고 전체 자동 처리")
    parser.add_argument("--no-video", action="store_true", help="영상 생성 건너뜀 (카드만)")
    parser.add_argument("--pages", type=int, default=3, help="공취사 크롤링 페이지 수")
    args = parser.parse_args()

    if args.company:
        run_pipeline(args.company, make_video_flag=not args.no_video)
    elif args.auto:
        run_auto_pipeline(pages=args.pages)
    else:
        parser.print_help()
        print("\n예시:")
        print("  python main.py --company '한국전력공사'")
        print("  python main.py --company '한국수자원공사' --no-video")
        print("  python main.py --auto --pages 5")


if __name__ == "__main__":
    main()
