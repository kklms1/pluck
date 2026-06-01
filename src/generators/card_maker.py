"""
연차별 연봉 카드 이미지 생성기
- 유튜브 영상용 카드형 위젯 (1920x1080)
- 기업 CI 색상 적용
- 연차/직급/실수령액 레이아웃
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
from dataclasses import dataclass
from typing import Optional
import math

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../../output/images")
FONT_DIR = os.path.join(os.path.dirname(__file__), "../../assets/fonts")

# 기본 컬러 팔레트
PALETTE = {
    "bg_dark": (12, 15, 25),
    "bg_card": (22, 28, 45),
    "accent_blue": (64, 156, 255),
    "accent_gold": (255, 196, 60),
    "accent_green": (52, 211, 153),
    "text_white": (255, 255, 255),
    "text_gray": (160, 170, 190),
    "text_dim": (90, 100, 120),
    "grade_bar": (40, 50, 75),
}

CANVAS_W, CANVAS_H = 1920, 1080


@dataclass
class CardData:
    company_name: str
    year: int                  # 연차
    grade: str                 # 직급
    annual_gross_10k: int      # 세전연봉
    monthly_gross_10k: float   # 월 세전
    monthly_net_10k: float     # 월 실수령
    tax_rate_pct: float        # 공제율
    insurance_10k: float       # 월 4대보험
    income_tax_10k: float      # 월 소득세
    company_color: tuple = (64, 156, 255)   # 기업 CI 색상
    company_logo_path: Optional[str] = None


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """나눔고딕 or 폴백 폰트 로드"""
    names = ["NanumGothicBold.ttf" if bold else "NanumGothic.ttf",
             "NotoSansKR-Bold.ttf" if bold else "NotoSansKR-Regular.ttf"]
    for name in names:
        path = os.path.join(FONT_DIR, name)
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    # 시스템 폰트 폴백
    for sys_path in ["/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
                     "/System/Library/Fonts/AppleSDGothicNeo.ttc"]:
        if os.path.exists(sys_path):
            return ImageFont.truetype(sys_path, size)
    return ImageFont.load_default()


def _draw_rounded_rect(draw: ImageDraw.Draw, xy, radius: int, fill, outline=None, width=1):
    x1, y1, x2, y2 = xy
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
    draw.ellipse([x1, y1, x1 + radius * 2, y1 + radius * 2], fill=fill)
    draw.ellipse([x2 - radius * 2, y1, x2, y1 + radius * 2], fill=fill)
    draw.ellipse([x1, y2 - radius * 2, x1 + radius * 2, y2], fill=fill)
    draw.ellipse([x2 - radius * 2, y2 - radius * 2, x2, y2], fill=fill)
    if outline:
        draw.rounded_rectangle(xy, radius=radius, outline=outline, width=width)


def _draw_glow(img: Image.Image, color: tuple, xy, radius: int = 60) -> Image.Image:
    """발광 효과 오버레이"""
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(glow)
    cx = (xy[0] + xy[2]) // 2
    cy = (xy[1] + xy[3]) // 2
    for r in range(radius, 0, -10):
        alpha = int(30 * (1 - r / radius))
        g_draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=20))
    return Image.alpha_composite(img.convert("RGBA"), glow)


def make_salary_card(data: CardData, output_path: str = None) -> str:
    """연차별 연봉 카드 1장 생성"""
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), PALETTE["bg_dark"])
    draw = ImageDraw.Draw(img)
    accent = data.company_color

    # 배경 그라디언트 효과 (수동)
    for y in range(CANVAS_H):
        alpha = int(15 * (1 - y / CANVAS_H))
        draw.line([(0, y), (CANVAS_W, y)], fill=(accent[0], accent[1], accent[2]))
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), PALETTE["bg_dark"])
    draw = ImageDraw.Draw(img)

    # 좌상단 기업명 배지
    _draw_rounded_rect(draw, (60, 50, 420, 110), radius=20, fill=(*accent, 40) if len(accent) == 3 else accent)
    font_company = _load_font(36, bold=True)
    draw.text((80, 65), data.company_name, font=font_company, fill=accent)

    # 연차 대형 표시 (좌측)
    font_year_big = _load_font(200, bold=True)
    year_text = f"{data.year}"
    draw.text((80, 150), year_text, font=font_year_big, fill=(*accent, 180) if len(accent) == 4 else accent)
    font_year_label = _load_font(60, bold=False)
    draw.text((80, 380), "년차", font=font_year_label, fill=PALETTE["text_gray"])

    # 직급 태그
    font_grade = _load_font(44, bold=True)
    _draw_rounded_rect(draw, (80, 460, 300, 520), radius=15, fill=PALETTE["grade_bar"])
    draw.text((100, 470), data.grade, font=font_grade, fill=PALETTE["text_white"])

    # 메인 카드 (우측)
    card_x1, card_y1 = 550, 80
    card_x2, card_y2 = CANVAS_W - 60, CANVAS_H - 80
    _draw_rounded_rect(draw, (card_x1, card_y1, card_x2, card_y2), radius=30, fill=PALETTE["bg_card"])

    # 구분선
    draw.rectangle([card_x1 + 40, card_y1 + 100, card_x2 - 40, card_y1 + 102], fill=PALETTE["grade_bar"])

    # 실수령액 (메인 숫자)
    font_net_label = _load_font(38)
    font_net_value = _load_font(130, bold=True)
    font_sub = _load_font(44, bold=True)
    font_sub_label = _load_font(32)

    draw.text((card_x1 + 50, card_y1 + 30), "월 실수령액", font=font_net_label, fill=PALETTE["text_gray"])
    net_text = f"{data.monthly_net_10k:.0f}"
    draw.text((card_x1 + 50, card_y1 + 80), net_text, font=font_net_value, fill=PALETTE["accent_green"] if "accent_green" in PALETTE else accent)
    draw.text((card_x1 + 50 + len(net_text) * 68, card_y1 + 170), "만원", font=font_sub_label, fill=PALETTE["text_gray"])

    # 세부 정보 격자
    details = [
        ("세전 연봉", f"{data.annual_gross_10k:,}만원"),
        ("월 세전", f"{data.monthly_gross_10k:.0f}만원"),
        ("4대보험", f"{data.insurance_10k:.1f}만원"),
        ("소득세", f"{data.income_tax_10k:.1f}만원"),
        ("공제율", f"{data.tax_rate_pct:.1f}%"),
    ]

    grid_y = card_y1 + 420
    col_w = (card_x2 - card_x1 - 80) // 3
    for i, (label, value) in enumerate(details):
        col = i % 3
        row = i // 3
        gx = card_x1 + 50 + col * col_w
        gy = grid_y + row * 140

        _draw_rounded_rect(draw, (gx, gy, gx + col_w - 20, gy + 110), radius=16, fill=PALETTE["grade_bar"])
        draw.text((gx + 20, gy + 15), label, font=_load_font(28), fill=PALETTE["text_dim"])
        draw.text((gx + 20, gy + 55), value, font=_load_font(38, bold=True), fill=PALETTE["text_white"])

    # 하단 CTA 힌트
    font_cta = _load_font(32)
    draw.text((card_x1 + 50, card_y2 - 60), "▶ 자기소개서 & 기출변형문제 → 영상 하단 링크", font=font_cta, fill=PALETTE["text_dim"])

    # 저장
    os.makedirs(os.path.dirname(output_path) if output_path else OUTPUT_DIR, exist_ok=True)
    if not output_path:
        output_path = os.path.join(OUTPUT_DIR, f"{data.company_name}_{data.year}년차.png")
    img.save(output_path, "PNG", quality=95)
    return output_path


def make_card_sequence(
    company_name: str,
    salary_list: list,
    company_color: tuple = (64, 156, 255),
    output_dir: str = None,
) -> list[str]:
    """연차 전체 카드 시퀀스 생성"""
    out_dir = output_dir or os.path.join(OUTPUT_DIR, company_name)
    os.makedirs(out_dir, exist_ok=True)
    paths = []

    for item in salary_list:
        card = CardData(
            company_name=company_name,
            year=item["year"] if isinstance(item, dict) else item.year,
            grade=item["grade"] if isinstance(item, dict) else item.grade,
            annual_gross_10k=item["annual_gross_10k"] if isinstance(item, dict) else item.annual_gross_10k,
            monthly_gross_10k=item["monthly_gross_10k"] if isinstance(item, dict) else item.monthly_gross_10k,
            monthly_net_10k=item["monthly_net_10k"] if isinstance(item, dict) else item.monthly_net_10k,
            tax_rate_pct=item["tax_rate_pct"] if isinstance(item, dict) else item.tax_rate_pct,
            insurance_10k=item["insurance_10k"] if isinstance(item, dict) else item.insurance_10k,
            income_tax_10k=item["income_tax_10k"] if isinstance(item, dict) else item.income_tax_10k,
            company_color=company_color,
        )
        year_val = card.year
        path = os.path.join(out_dir, f"{year_val:02d}년차_{card.grade}.png")
        saved = make_salary_card(card, path)
        paths.append(saved)
        print(f"  생성됨: {saved}")

    return paths
