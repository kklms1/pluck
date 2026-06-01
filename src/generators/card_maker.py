"""
연차별 연봉 카드 이미지 생성기 (v2)
- 1920x1080 유튜브 영상용
- 후킹 카드: 월 실수령 + 세전연봉 동시 표시
- 연차 카드: 1~30년차 1년 단위
- 기업 CI 색상 적용
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
from dataclasses import dataclass
from typing import Optional

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../../output/images")
FONT_DIR = os.path.join(os.path.dirname(__file__), "../../assets/fonts")

PALETTE = {
    "bg_dark":    (12, 15, 25),
    "bg_card":    (22, 28, 45),
    "accent_green": (52, 211, 153),
    "accent_gold":  (255, 196, 60),
    "text_white": (255, 255, 255),
    "text_gray":  (160, 170, 190),
    "text_dim":   (90, 100, 120),
    "grade_bar":  (40, 50, 75),
    "divider":    (55, 65, 90),
}

CANVAS_W, CANVAS_H = 1920, 1080


@dataclass
class CardData:
    company_name: str
    year: int
    grade: str
    hobong: int
    annual_gross_10k: int       # 세전 연봉
    monthly_gross_10k: float    # 월 세전
    monthly_net_10k: float      # 월 실수령
    tax_rate_pct: float
    insurance_10k: float = 0
    income_tax_10k: float = 0
    company_color: tuple = (64, 156, 255)
    total_cards: int = 30       # 전체 카드 수 (진행 바용)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = (
        ["NanumGothicBold.ttf", "NotoSansKR-Bold.ttf"] if bold
        else ["NanumGothic.ttf", "NotoSansKR-Regular.ttf"]
    )
    for name in names:
        p = os.path.join(FONT_DIR, name)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    for sys_p in [
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf" if bold
        else "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        if os.path.exists(sys_p):
            return ImageFont.truetype(sys_p, size)
    return ImageFont.load_default()


def _rr(draw: ImageDraw.Draw, xy, r: int, fill, outline=None, width=2):
    """rounded rectangle"""
    draw.rounded_rectangle(xy, radius=r, fill=fill,
                           outline=outline, width=width)


def _progress_bar(draw: ImageDraw.Draw, current: int, total: int, accent: tuple):
    """하단 진행 바"""
    bar_h = 6
    y = CANVAS_H - bar_h
    draw.rectangle([0, y, CANVAS_W, CANVAS_H], fill=PALETTE["grade_bar"])
    filled_w = int(CANVAS_W * current / total)
    draw.rectangle([0, y, filled_w, CANVAS_H], fill=accent)


# ─────────────────────────────────────────────────────────────
# 1. 후킹 카드 (영상 오프닝 / 썸네일용)
# ─────────────────────────────────────────────────────────────

def make_hook_card(
    company_name: str,
    annual_gross_10k: int,
    monthly_net_10k: float,
    company_color: tuple = (64, 156, 255),
    output_path: str = None,
) -> str:
    """
    후킹용 카드: 세전연봉 + 월 실수령 두 숫자 동시 강조
    """
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), PALETTE["bg_dark"])
    draw = ImageDraw.Draw(img)
    accent = company_color

    # 배경 그라디언트 효과 (상단 accent 엣지)
    for y in range(8):
        alpha = int(200 * (1 - y / 8))
        draw.line([(0, y), (CANVAS_W, y)],
                  fill=(accent[0], accent[1], accent[2]))

    # 기업명 배지 (좌상단)
    _rr(draw, (60, 40, 480, 100), r=22,
        fill=(accent[0], accent[1], accent[2], 30) if len(accent) == 4 else PALETTE["grade_bar"],
        outline=accent, width=2)
    draw.text((90, 53), company_name,
              font=_font(38, bold=True), fill=accent)

    # "연봉 전격 공개" 서브타이틀
    draw.text((90, 120), "입사부터 30년차까지 · 세전 · 실수령 전부 공개",
              font=_font(32), fill=PALETTE["text_dim"])

    # ── 좌측 패널: 세전연봉 ──────────────────────────────
    lx1, ly1, lx2, ly2 = 60, 200, 880, 960
    _rr(draw, (lx1, ly1, lx2, ly2), r=30, fill=PALETTE["bg_card"])

    draw.text((lx1 + 50, ly1 + 40), "세전 연봉",
              font=_font(40), fill=PALETTE["text_gray"])
    draw.text((lx1 + 50, ly1 + 95), "(신입 기준)",
              font=_font(30), fill=PALETTE["text_dim"])

    gross_str = f"{annual_gross_10k:,}"
    draw.text((lx1 + 50, ly1 + 180), gross_str,
              font=_font(180, bold=True), fill=PALETTE["text_white"])
    draw.text((lx1 + 50 + len(gross_str) * 95, ly1 + 295), "만원",
              font=_font(60), fill=PALETTE["text_gray"])

    draw.text((lx1 + 50, ly1 + 400), f"월 세전  {annual_gross_10k/12:.0f}만원",
              font=_font(42), fill=PALETTE["text_dim"])

    # ── 우측 패널: 월 실수령 (강조) ──────────────────────
    rx1, ry1, rx2, ry2 = 920, 200, 1860, 960
    _rr(draw, (rx1, ry1, rx2, ry2), r=30, fill=PALETTE["bg_card"])

    # 강조 배지
    _rr(draw, (rx1 + 50, ry1 + 40, rx1 + 280, ry1 + 100), r=16,
        fill=PALETTE["accent_green"])
    draw.text((rx1 + 70, ry1 + 52), "월 실수령",
              font=_font(38, bold=True), fill=PALETTE["bg_dark"])

    net_str = f"{monthly_net_10k:.0f}"
    draw.text((rx1 + 50, ry1 + 130), net_str,
              font=_font(240, bold=True), fill=PALETTE["accent_green"])
    draw.text((rx1 + 50 + len(net_str) * 125, ry1 + 320), "만원",
              font=_font(72), fill=PALETTE["accent_green"])

    draw.text((rx1 + 50, ry1 + 480),
              "※ 4대보험 + 소득세 공제 후 실제 통장 입금액",
              font=_font(34), fill=PALETTE["text_dim"])

    # 하단 안내
    draw.text((CANVAS_W // 2 - 300, CANVAS_H - 80),
              "▼  1년차부터 30년차까지 바로 공개  ▼",
              font=_font(36, bold=True), fill=accent)

    _save(img, output_path or os.path.join(OUTPUT_DIR, f"{company_name}_후킹카드.png"))
    return output_path or os.path.join(OUTPUT_DIR, f"{company_name}_후킹카드.png")


# ─────────────────────────────────────────────────────────────
# 2. 연차별 카드 (1~30년차)
# ─────────────────────────────────────────────────────────────

def make_salary_card(data: CardData, output_path: str = None) -> str:
    """
    연차 카드 1장:
    좌 — 연차/직급/호봉 대형 표시
    우 — 세전연봉 + 월 실수령 두 숫자 강조
    하단 — 진행 바
    """
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), PALETTE["bg_dark"])
    draw = ImageDraw.Draw(img)
    accent = data.company_color

    # 상단 엣지 라인
    draw.rectangle([0, 0, CANVAS_W, 6], fill=accent)

    # 기업명 (좌상단)
    _rr(draw, (40, 25, 360, 80), r=18, fill=PALETTE["grade_bar"])
    draw.text((60, 35), data.company_name,
              font=_font(32, bold=True), fill=accent)

    # 카드 인덱스 (우상단)
    draw.text((CANVAS_W - 160, 30),
              f"{data.year}/30",
              font=_font(30), fill=PALETTE["text_dim"])

    # ── 좌측: 연차/직급/호봉 ──────────────────────────────
    # 연차 대형 숫자
    year_str = str(data.year)
    draw.text((60, 120), year_str,
              font=_font(320, bold=True), fill=accent)
    draw.text((60 + len(year_str) * 165, 370), "년차",
              font=_font(72), fill=PALETTE["text_gray"])

    # 직급 태그
    _rr(draw, (60, 470, 60 + len(data.grade) * 38 + 40, 540),
        r=14, fill=PALETTE["grade_bar"])
    draw.text((80, 480), data.grade,
              font=_font(48, bold=True), fill=PALETTE["text_white"])

    # 호봉
    draw.text((60, 560), f"{data.hobong}호봉",
              font=_font(36), fill=PALETTE["text_dim"])

    # 구분선
    draw.rectangle([490, 100, 494, CANVAS_H - 80], fill=PALETTE["divider"])

    # ── 우측 상단: 세전연봉 ──────────────────────────────
    rx = 540
    draw.text((rx, 100), "세전 연봉",
              font=_font(36), fill=PALETTE["text_gray"])

    gross_str = f"{data.annual_gross_10k:,}만원"
    draw.text((rx, 145), gross_str,
              font=_font(90, bold=True), fill=PALETTE["text_white"])

    draw.text((rx, 255), f"월 세전  {data.monthly_gross_10k:.0f}만원",
              font=_font(38), fill=PALETTE["text_dim"])

    # 구분선 (가로)
    draw.rectangle([rx, 310, CANVAS_W - 60, 313], fill=PALETTE["divider"])

    # ── 우측 하단: 월 실수령 (강조) ──────────────────────
    _rr(draw, (rx, 330, rx + 300, 400), r=16,
        fill=PALETTE["accent_green"])
    draw.text((rx + 20, 342), "월 실수령",
              font=_font(40, bold=True), fill=PALETTE["bg_dark"])

    net_str = f"{data.monthly_net_10k:.0f}만원"
    draw.text((rx, 415), net_str,
              font=_font(160, bold=True), fill=PALETTE["accent_green"])

    # 세부 공제 정보
    detail_y = 610
    draw.text((rx, detail_y),
              f"4대보험  {data.insurance_10k:.1f}만  +  소득세  {data.income_tax_10k:.1f}만  =  공제 {data.tax_rate_pct:.1f}%",
              font=_font(30), fill=PALETTE["text_dim"])

    # ── 마일스톤 강조 (5의 배수 연차) ────────────────────
    if data.year % 5 == 0:
        _rr(draw, (rx, 660, rx + 420, 730), r=14,
            fill=(accent[0] // 4, accent[1] // 4, accent[2] // 4))
        yoy = ""
        draw.text((rx + 15, 673),
                  f"▲ {data.year}년차 도달 · " + yoy,
                  font=_font(32), fill=accent)

    # ── 하단 진행 바 ──────────────────────────────────────
    _progress_bar(draw, data.year, data.total_cards, accent)

    path = output_path or os.path.join(
        OUTPUT_DIR, f"{data.company_name}_{data.year:02d}년차.png")
    _save(img, path)
    return path


# ─────────────────────────────────────────────────────────────
# 3. 섹션 전환 카드
# ─────────────────────────────────────────────────────────────

def make_section_card(
    company_name: str,
    section_title: str,
    section_subtitle: str,
    company_color: tuple = (64, 156, 255),
    output_path: str = None,
) -> str:
    """씬 전환용 카드 (복지, 숨겨진 혜택 등 섹션 구분)"""
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), PALETTE["bg_dark"])
    draw = ImageDraw.Draw(img)
    accent = company_color

    # 중앙 수평선
    cy = CANVAS_H // 2
    draw.rectangle([0, cy - 2, CANVAS_W, cy + 2], fill=accent)

    # 기업명 (상단)
    draw.text((CANVAS_W // 2, cy - 140),
              company_name, font=_font(42), fill=PALETTE["text_dim"],
              anchor="mm")

    # 섹션 제목 (대형)
    draw.text((CANVAS_W // 2, cy + 60),
              section_title, font=_font(120, bold=True),
              fill=PALETTE["text_white"], anchor="mm")

    # 섹션 부제
    draw.text((CANVAS_W // 2, cy + 180),
              section_subtitle, font=_font(40),
              fill=accent, anchor="mm")

    path = output_path or os.path.join(
        OUTPUT_DIR, f"{company_name}_섹션_{section_title}.png")
    _save(img, path)
    return path


# ─────────────────────────────────────────────────────────────
# 4. 시퀀스 생성 (전체 카드셋)
# ─────────────────────────────────────────────────────────────

def make_card_sequence(
    company_name: str,
    salary_list: list,
    company_color: tuple = (64, 156, 255),
    output_dir: str = None,
) -> dict[str, list[str]]:
    """
    전체 카드 시퀀스 생성
    Returns:
        {
          "hook":     [후킹카드 경로],
          "salary":   [1년차 ~ 30년차 카드 경로들],
          "sections": [섹션 전환 카드들],
        }
    """
    out_dir = output_dir or os.path.join(OUTPUT_DIR, company_name)
    os.makedirs(out_dir, exist_ok=True)

    items = [
        (s if isinstance(s, dict) else s.__dict__)
        for s in salary_list
    ]
    total = len(items)

    # 후킹 카드 (신입 기준)
    first = items[0] if items else {}
    hook_path = make_hook_card(
        company_name=company_name,
        annual_gross_10k=first.get("annual_gross_10k", 0),
        monthly_net_10k=first.get("monthly_net_10k", 0),
        company_color=company_color,
        output_path=os.path.join(out_dir, "00_후킹카드.png"),
    )
    print(f"  [후킹] {hook_path}")

    # 섹션 카드
    section_paths = []
    for title, subtitle in [
        ("복지  수당", "연봉에 이것까지 더하면?"),
        ("숨겨진  혜택", "아무도 말 안 해준 진짜 복지"),
        ("성장  가능성", "10년 후 나의 커리어는?"),
    ]:
        sp = make_section_card(
            company_name, title, subtitle, company_color,
            output_path=os.path.join(out_dir, f"섹션_{title.replace(' ','')}.png"),
        )
        section_paths.append(sp)

    # 연차별 카드 1~N년
    salary_paths = []
    for item in items:
        card = CardData(
            company_name=company_name,
            year=item.get("career_year", item.get("year", 0)),
            grade=item.get("grade", ""),
            hobong=item.get("hobong", 0),
            annual_gross_10k=item.get("annual_gross_10k", 0),
            monthly_gross_10k=item.get("monthly_gross_10k", 0),
            monthly_net_10k=item.get("monthly_net_10k", 0),
            tax_rate_pct=item.get("tax_rate_pct", 0),
            insurance_10k=item.get("insurance_10k", 0),
            income_tax_10k=item.get("income_tax_10k", 0),
            company_color=company_color,
            total_cards=total,
        )
        yr = card.year
        path = os.path.join(out_dir, f"{yr:02d}년차_{card.grade}.png")
        saved = make_salary_card(card, path)
        salary_paths.append(saved)
        print(f"  [{yr:2d}년차] {saved}")

    return {
        "hook": [hook_path],
        "salary": salary_paths,
        "sections": section_paths,
    }


def make_welfare_card(
    company_name: str,
    welfare: dict = None,        # welfare_parser 결과 (항목별 만원/년)
    training: dict = None,       # 교육훈련비 결과
    company_color: tuple = (64, 156, 255),
    output_path: str = None,
) -> str:
    """
    복지·수당 카드: 복리후생비 항목별 + 교육훈련비를 시각화
    값은 연 기준(만원)이며 월 환산도 병기
    """
    welfare = welfare or {}
    training = training or {}
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), PALETTE["bg_dark"])
    draw = ImageDraw.Draw(img)
    accent = company_color

    draw.rectangle([0, 0, CANVAS_W, 6], fill=accent)
    draw.text((60, 40), company_name, font=_font(40, bold=True), fill=accent)
    draw.text((60, 95), "복리후생 · 1인당 지원 금액 (공시 기준)",
              font=_font(32), fill=PALETTE["text_dim"])

    # 항목 정의 (label, key, 아이콘 텍스트)
    rows = [
        ("식대",          "meal_10k"),
        ("교통·주유",     "transport_10k"),
        ("의료·건강검진", "medical_10k"),
        ("학자금·보육",   "childcare_tuition_10k"),
        ("주택·사택대출", "housing_loan_10k"),
        ("문화·여가",     "recreation_10k"),
        ("복지포인트",    "welfare_point_10k"),
    ]
    present = [(lbl, welfare.get(key, 0)) for lbl, key in rows if welfare.get(key, 0)]

    max_val = max((v for _, v in present), default=1) or 1
    y = 180
    row_h = 92
    for label, val in present[:7]:
        draw.text((90, y), label, font=_font(38, bold=True), fill=PALETTE["text_white"])
        # 바
        bar_x = 480
        bar_full = 900
        _rr(draw, (bar_x, y + 12, bar_x + bar_full, y + 44), r=8, fill=PALETTE["grade_bar"])
        filled = int(bar_full * val / max_val)
        if filled > 0:
            _rr(draw, (bar_x, y + 12, bar_x + filled, y + 44), r=8, fill=accent)
        # 금액
        draw.text((bar_x + bar_full + 30, y),
                  f"{val:,.0f}만원/년", font=_font(34, bold=True), fill=PALETTE["accent_green"])
        draw.text((bar_x + bar_full + 30, y + 44),
                  f"월 {val/12:.1f}만원", font=_font(26), fill=PALETTE["text_dim"])
        y += row_h

    if not present:
        draw.text((90, 220), "복리후생 공시 데이터 없음",
                  font=_font(44), fill=PALETTE["text_dim"])

    # 총액 + 교육훈련비 요약 박스 (하단)
    total = welfare.get("total_per_person_10k", sum(v for _, v in present))
    box_y = CANVAS_H - 180
    _rr(draw, (60, box_y, CANVAS_W - 60, CANVAS_H - 50), r=20, fill=PALETTE["bg_card"])
    if total:
        draw.text((100, box_y + 30), "1인당 복리후생비 총액",
                  font=_font(34), fill=PALETTE["text_gray"])
        draw.text((100, box_y + 70), f"연 {total:,.0f}만원",
                  font=_font(56, bold=True), fill=PALETTE["text_white"])
    per_train = training.get("per_person_10k", 0)
    if per_train:
        draw.text((CANVAS_W - 720, box_y + 30), "1인당 교육훈련비",
                  font=_font(34), fill=PALETTE["text_gray"])
        draw.text((CANVAS_W - 720, box_y + 70), f"연 {per_train:,.0f}만원",
                  font=_font(56, bold=True), fill=PALETTE["accent_gold"])

    if output_path is None:
        out_dir = os.path.join(OUTPUT_DIR, "welfare")
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, f"{company_name}_복지.png")
    _save(img, output_path)
    return output_path


def make_benefit_card(
    company_name: str,
    leave: dict = None,          # welfare_parser.parse_leave_policy 결과
    company_color: tuple = (64, 156, 255),
    output_path: str = None,
) -> str:
    """
    숨겨진 혜택 카드: 휴가/휴직 정책 + 제도 플래그(유연근무/재택/해외연수 등)
    """
    leave = leave or {}
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), PALETTE["bg_dark"])
    draw = ImageDraw.Draw(img)
    accent = company_color

    draw.rectangle([0, 0, CANVAS_W, 6], fill=accent)
    draw.text((60, 40), company_name, font=_font(40, bold=True), fill=accent)
    draw.text((60, 95), "휴가 · 휴직 · 제도  (취업규칙 기준)",
              font=_font(32), fill=PALETTE["text_dim"])

    # 좌측: 숫자형 휴가 지표
    metrics = []
    if leave.get("annual_leave_max"):
        metrics.append(("연차", f"최대 {leave['annual_leave_max']}일"))
    if leave.get("summer_leave_days"):
        metrics.append(("하계휴가", f"{leave['summer_leave_days']}일 (별도)"))
    if leave.get("sick_paid_days"):
        metrics.append(("유급병가", f"{leave['sick_paid_days']}일"))
    if leave.get("parental_leave_months"):
        metrics.append(("육아휴직", f"{leave['parental_leave_months']}개월"))
    if leave.get("marriage_days"):
        metrics.append(("결혼휴가", f"{leave['marriage_days']}일"))

    y = 200
    for label, val in metrics[:6]:
        _rr(draw, (60, y, 880, y + 90), r=16, fill=PALETTE["bg_card"])
        draw.text((90, y + 22), label, font=_font(38, bold=True), fill=PALETTE["text_gray"])
        draw.text((480, y + 18), val, font=_font(44, bold=True), fill=PALETTE["accent_green"])
        y += 110

    # 우측: 제도 플래그 체크 그리드
    flags = [
        ("유연근무제",   "flexible_work"),
        ("재택근무",     "remote_work"),
        ("해외연수",     "overseas_training"),
        ("어학연수",     "language_training"),
        ("MBA·학위지원", "mba_support"),
        ("학습휴직",     "study_leave"),
        ("리프레시휴직", "career_break"),
    ]
    fx = 940
    fy = 200
    draw.text((fx, 150), "운영 제도", font=_font(34), fill=PALETTE["text_dim"])
    for label, key in flags:
        on = bool(leave.get(key))
        mark = "✅" if on else "—"
        color = PALETTE["accent_green"] if on else PALETTE["text_dim"]
        _rr(draw, (fx, fy, CANVAS_W - 60, fy + 80), r=14,
            fill=PALETTE["bg_card"] if on else PALETTE["bg_dark"],
            outline=PALETTE["grade_bar"], width=1)
        draw.text((fx + 30, fy + 18), label,
                  font=_font(38, bold=on), fill=PALETTE["text_white"] if on else PALETTE["text_dim"])
        draw.text((CANVAS_W - 130, fy + 14), mark, font=_font(40), fill=color)
        fy += 95

    if output_path is None:
        out_dir = os.path.join(OUTPUT_DIR, "benefit")
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, f"{company_name}_혜택.png")
    _save(img, output_path)
    return output_path


def make_location_card(
    company_name: str,
    location: dict = None,       # src.data.location.get_location_dict() 결과
    company_color: tuple = (64, 156, 255),
    output_path: str = None,
) -> str:
    """
    근무지 카드: 본사 위치 + 지방이전 여부 + 순환/업무순환 강도
    지방 취준생이 연봉만큼 중요하게 보는 정보.
    """
    location = location or {}
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), PALETTE["bg_dark"])
    draw = ImageDraw.Draw(img)
    accent = company_color

    draw.rectangle([0, 0, CANVAS_W, 6], fill=accent)
    draw.text((60, 40), company_name, font=_font(40, bold=True), fill=accent)
    draw.text((60, 95), "근무지 · 지방이전 · 순환근무",
              font=_font(32), fill=PALETTE["text_dim"])

    # ── 본사 위치 (대형) ─────────────────────────────────────
    y = 190
    draw.text((90, y), "🏢 본사", font=_font(40), fill=PALETTE["text_gray"])
    region = location.get("region", "")
    draw.text((90, y + 55), region or "—",
              font=_font(96, bold=True), fill=PALETTE["text_white"])
    draw.text((90, y + 175), location.get("hq_address", ""),
              font=_font(36), fill=PALETTE["text_gray"])

    # ── 지방이전 배지 ────────────────────────────────────────
    by = 470
    relocated = location.get("relocated", False)
    inno = location.get("innovation_city", "")
    badge_color = PALETTE["accent_gold"] if relocated else PALETTE["grade_bar"]
    badge_text = f"지방이전 완료 · {inno}" if relocated else "지방이전 비대상 (현 위치 유지)"
    _rr(draw, (90, by, 90 + len(badge_text) * 24 + 60, by + 64), r=16, fill=badge_color)
    draw.text((120, by + 14), badge_text, font=_font(34, bold=True),
              fill=PALETTE["bg_dark"] if relocated else PALETTE["text_gray"])

    # ── 순환근무 강도 ────────────────────────────────────────
    ry = 600
    rotation = location.get("rotation", "")
    note = location.get("rotation_note", "")
    scope = location.get("branch_scope", "")

    _rr(draw, (60, ry, CANVAS_W - 60, CANVAS_H - 60), r=24, fill=PALETTE["bg_card"])
    draw.text((100, ry + 30), "🔄 근무형태", font=_font(36), fill=PALETTE["text_gray"])

    # 강도 시각화 (전국순환=3칸, 권역=2칸, 본사상주=1칸)
    level = {"전국순환": 3, "권역순환": 2, "본사상주": 1}.get(rotation, 0)
    draw.text((100, ry + 80), rotation or "정보 없음",
              font=_font(72, bold=True),
              fill=PALETTE["accent_green"] if level <= 1 else
                   (PALETTE["accent_gold"] if level == 2 else (255, 120, 110)))

    # 강도 인디케이터 (이사 빈도 ↑일수록 빨강)
    ix = 100
    iy = ry + 190
    labels3 = ["적음", "보통", "잦음"]
    for i in range(3):
        on = i < level
        col = [(110, 200, 130), (255, 196, 60), (255, 110, 100)][i]
        _rr(draw, (ix, iy, ix + 220, iy + 50), r=12,
            fill=col if on else PALETTE["grade_bar"])
        draw.text((ix + 70, iy + 8), labels3[i], font=_font(30, bold=True),
                  fill=PALETTE["bg_dark"] if on else PALETTE["text_dim"])
        ix += 240
    draw.text((100 + 720 + 40, iy + 8), "← 이사·전보 빈도",
              font=_font(28), fill=PALETTE["text_dim"])

    if note:
        draw.text((100, ry + 270), f"· {note}",
                  font=_font(34), fill=PALETTE["text_white"])
    if scope:
        draw.text((100, ry + 320), f"· {scope}",
                  font=_font(34), fill=PALETTE["text_gray"])

    if output_path is None:
        out_dir = os.path.join(OUTPUT_DIR, "location")
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, f"{company_name}_근무지.png")
    _save(img, output_path)
    return output_path


def make_company_profile_card(
    company_name: str,
    total_assets_100m: int = 0,      # 자산총계 (억원)
    asset_rank: int = 0,             # 공공기관 자산 순위
    employee_count: int = 0,         # 임직원 수
    revenue_100m: int = 0,           # 영업수익 (억원)
    blind_overall: float = 0.0,      # 블라인드 종합 평점
    blind_salary: float = 0.0,       # 급여·복지
    blind_worklife: float = 0.0,     # 워라밸
    blind_culture: float = 0.0,      # 사내문화
    blind_review_count: int = 0,
    blind_screenshot_path: str = "",  # 블라인드 스크린샷 (있으면 삽입)
    company_color: tuple = (64, 156, 255),
    output_path: str = None,
) -> str:
    """
    기업 규모 카드: 자산총계/순위 + 블라인드 평점 한 장에 표시
    Layout:
      상단 절반 — 자산/규모 지표 (3 stat 블록)
      하단 절반 — 블라인드 평점 (별점 + 항목별 바)
    """
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), PALETTE["bg_dark"])
    draw = ImageDraw.Draw(img)
    accent = company_color

    # 상단 accent 라인
    for y in range(6):
        draw.line([(0, y), (CANVAS_W, y)], fill=accent)

    # 기업명 + 섹션 타이틀
    draw.text((60, 40), company_name,
              font=_font(44, bold=True), fill=accent)
    draw.text((60, 100), "기업 규모 · 블라인드 직원 평가",
              font=_font(32), fill=PALETTE["text_dim"])

    # ── 상단 절반: 자산 지표 ─────────────────────────────────────
    stat_y1, stat_y2 = 160, 490
    stat_blocks = []
    if total_assets_100m > 0:
        stat_blocks.append(("자산총계", f"{total_assets_100m:,}", "억원"))
    if asset_rank > 0:
        stat_blocks.append(("공공기관 자산순위", f"{asset_rank}", "위"))
    if employee_count > 0:
        stat_blocks.append(("임직원 수", f"{employee_count:,}", "명"))
    if revenue_100m > 0 and len(stat_blocks) < 3:
        stat_blocks.append(("영업수익", f"{revenue_100m:,}", "억원"))

    # 최대 3개 블록을 균등 배치
    if stat_blocks:
        cols = min(len(stat_blocks), 3)
        blk_w = (CANVAS_W - 120) // cols
        for i, (label, value, unit) in enumerate(stat_blocks[:3]):
            bx1 = 60 + i * blk_w
            bx2 = bx1 + blk_w - 20
            _rr(draw, (bx1, stat_y1, bx2, stat_y2), r=24, fill=PALETTE["bg_card"])

            draw.text((bx1 + 30, stat_y1 + 28), label,
                      font=_font(34), fill=PALETTE["text_gray"])

            val_font_size = 110 if len(value) <= 5 else 80
            draw.text((bx1 + 30, stat_y1 + 80), value,
                      font=_font(val_font_size, bold=True), fill=PALETTE["text_white"])
            draw.text((bx1 + 30, stat_y1 + 210), unit,
                      font=_font(40), fill=PALETTE["text_dim"])

            # 순위 카드에는 강조 배지
            if "순위" in label and asset_rank > 0:
                badge_text = "TOP" if asset_rank <= 10 else f"#{asset_rank}"
                _rr(draw, (bx1 + 30, stat_y1 + 260, bx1 + 180, stat_y1 + 310), r=14,
                    fill=PALETTE["accent_gold"] if asset_rank <= 10 else PALETTE["grade_bar"])
                draw.text((bx1 + 50, stat_y1 + 268), badge_text,
                          font=_font(30, bold=True),
                          fill=PALETTE["bg_dark"] if asset_rank <= 10 else PALETTE["text_gray"])

    # ── 하단 절반: 블라인드 평점 ─────────────────────────────────
    blind_y1 = 510
    _rr(draw, (60, blind_y1, CANVAS_W - 60, CANVAS_H - 40), r=24,
        fill=PALETTE["bg_card"])

    # 블라인드 로고 텍스트
    draw.text((100, blind_y1 + 28), "BLIND",
              font=_font(36, bold=True), fill=(100, 160, 255))
    draw.text((240, blind_y1 + 35), "직원 평가",
              font=_font(30), fill=PALETTE["text_gray"])

    if blind_review_count > 0:
        draw.text((CANVAS_W - 350, blind_y1 + 35), f"리뷰 {blind_review_count:,}개",
                  font=_font(28), fill=PALETTE["text_dim"])

    if blind_overall > 0:
        # 종합 평점 (좌측 큰 숫자)
        draw.text((100, blind_y1 + 90), f"{blind_overall:.1f}",
                  font=_font(160, bold=True), fill=PALETTE["accent_green"])
        draw.text((100, blind_y1 + 260), "/ 5.0",
                  font=_font(48), fill=PALETTE["text_dim"])

        # 별점 시각화
        stars_filled = round(blind_overall)
        star_x = 100
        for i in range(5):
            color = PALETTE["accent_gold"] if i < stars_filled else PALETTE["grade_bar"]
            draw.text((star_x, blind_y1 + 320), "★",
                      font=_font(48, bold=True), fill=color)
            star_x += 58

        # 항목별 평점 바 (우측)
        cat_items = [
            ("급여·복지", blind_salary),
            ("워라밸",    blind_worklife),
            ("사내문화",  blind_culture),
        ]
        bar_x1 = 650
        bar_y = blind_y1 + 90
        for cat_label, cat_score in cat_items:
            if cat_score <= 0:
                continue
            draw.text((bar_x1, bar_y), cat_label,
                      font=_font(34), fill=PALETTE["text_gray"])
            draw.text((bar_x1 + 280, bar_y), f"{cat_score:.1f}",
                      font=_font(34, bold=True), fill=PALETTE["text_white"])

            # 5점 만점 바
            bar_full_w = 900
            bar_h2 = 16
            _rr(draw, (bar_x1, bar_y + 46, bar_x1 + bar_full_w, bar_y + 46 + bar_h2),
                r=8, fill=PALETTE["grade_bar"])
            filled = int(bar_full_w * cat_score / 5.0)
            if filled > 0:
                _rr(draw, (bar_x1, bar_y + 46, bar_x1 + filled, bar_y + 46 + bar_h2),
                    r=8, fill=PALETTE["accent_green"])

            bar_y += 130
    else:
        # 블라인드 데이터 없음
        draw.text((100, blind_y1 + 140), "블라인드 평점 데이터 없음",
                  font=_font(48), fill=PALETTE["text_dim"])

    # 블라인드 스크린샷 삽입 (있으면 우측 하단에)
    if blind_screenshot_path and os.path.exists(blind_screenshot_path):
        try:
            ss = Image.open(blind_screenshot_path).convert("RGB")
            ss_max_w, ss_max_h = 580, 400
            ss.thumbnail((ss_max_w, ss_max_h), Image.LANCZOS)
            ss_x = CANVAS_W - ss.width - 80
            ss_y = CANVAS_H - ss.height - 60
            img.paste(ss, (ss_x, ss_y))
            # 테두리
            draw2 = ImageDraw.Draw(img)
            draw2.rectangle([ss_x - 2, ss_y - 2,
                              ss_x + ss.width + 2, ss_y + ss.height + 2],
                             outline=accent, width=3)
        except Exception:
            pass

    if output_path is None:
        out_dir = os.path.join(OUTPUT_DIR, "profile")
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, f"{company_name}_기업규모.png")

    _save(img, output_path)
    return output_path


def _save(img: Image.Image, path: str):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    img.save(path, "PNG", quality=95)
