"""
알리오 공시 데이터 + 취업규칙 PDF/HWP → 복지/휴가/해외연수 파싱

파싱 대상:
  [알리오 공시] 복리후생비, 교육훈련비, 노동조합, 직원현황
  [취업규칙]    연차·휴가·휴직·해외연수·유연근무 조항
"""

import re
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)


# ── 복리후생비 공시 파서 ──────────────────────────────────────────────

@dataclass
class WelfareSummary:
    company_name: str
    year: int
    total_per_person_10k: float = 0    # 1인당 복리후생비 합계 (만원/년)

    # 알리오 공시 항목 (기관마다 공시 항목 다름)
    meal_10k: float = 0                # 식대 (연간)
    transport_10k: float = 0           # 교통비
    medical_10k: float = 0             # 의료비·건강검진
    childcare_tuition_10k: float = 0   # 어린이집·학자금
    housing_loan_10k: float = 0        # 주택대출·사택
    recreation_10k: float = 0          # 문화·체육·여가
    welfare_point_10k: float = 0       # 복지포인트·선택복지
    long_service_10k: float = 0        # 장기근속 포상
    other_10k: float = 0               # 기타


WELFARE_FIELD_MAP = {
    "식대": "meal_10k",
    "중식비": "meal_10k",
    "교통비": "transport_10k",
    "통근비": "transport_10k",
    "의료비": "medical_10k",
    "건강검진": "medical_10k",
    "학자금": "childcare_tuition_10k",
    "보육": "childcare_tuition_10k",
    "어린이집": "childcare_tuition_10k",
    "주택": "housing_loan_10k",
    "사택": "housing_loan_10k",
    "문화": "recreation_10k",
    "여가": "recreation_10k",
    "체육": "recreation_10k",
    "복지포인트": "welfare_point_10k",
    "선택복지": "welfare_point_10k",
    "장기근속": "long_service_10k",
}


def parse_welfare_tables(company_name: str, tables: list) -> list[WelfareSummary]:
    """알리오 복리후생비 공시 테이블 → WelfareSummary"""
    results = []

    for table in tables:
        if not table or len(table) < 2:
            continue

        header = [str(c).strip() for c in table[0]]
        year_col = _find_col(header, ["연도", "연"])
        total_col = _find_col(header, ["합계", "총계", "복리후생비", "1인당"])

        for row in table[1:]:
            if not row:
                continue
            row = [str(c).strip() for c in row]

            year = _parse_year(row[year_col] if year_col is not None else row[0])
            if not year:
                continue

            ws = WelfareSummary(company_name=company_name, year=year)

            if total_col is not None and total_col < len(row):
                ws.total_per_person_10k = _parse_money(row[total_col])

            # 컬럼별 항목 매핑
            for i, h in enumerate(header):
                if i >= len(row):
                    break
                field_name = _map_welfare_field(h)
                if field_name and row[i]:
                    val = _parse_money(row[i])
                    if val > 0:
                        setattr(ws, field_name, val)

            if ws.total_per_person_10k > 0 or _any_field_set(ws):
                results.append(ws)

    return results


# ── 교육훈련비 공시 파서 ──────────────────────────────────────────────

@dataclass
class TrainingSummary:
    company_name: str
    year: int
    total_10k: float = 0              # 교육훈련비 총액
    per_person_10k: float = 0         # 1인당 교육훈련비
    overseas_expense_10k: float = 0   # 해외 교육훈련비
    domestic_expense_10k: float = 0   # 국내 교육훈련비
    overseas_trainees: int = 0        # 해외 파견 인원


def parse_training_tables(company_name: str, tables: list) -> list[TrainingSummary]:
    results = []

    for table in tables:
        if not table or len(table) < 2:
            continue
        header = [str(c).strip() for c in table[0]]

        year_col = _find_col(header, ["연도", "연"])
        total_col = _find_col(header, ["합계", "총계", "교육훈련비"])
        pp_col = _find_col(header, ["1인당"])
        overseas_col = _find_col(header, ["해외", "국외"])
        domestic_col = _find_col(header, ["국내"])

        for row in table[1:]:
            if not row:
                continue
            row = [str(c).strip() for c in row]
            year = _parse_year(row[year_col] if year_col is not None else row[0])
            if not year:
                continue

            ts = TrainingSummary(company_name=company_name, year=year)
            if total_col and total_col < len(row):
                ts.total_10k = _parse_money(row[total_col])
            if pp_col and pp_col < len(row):
                ts.per_person_10k = _parse_money(row[pp_col])
            if overseas_col and overseas_col < len(row):
                ts.overseas_expense_10k = _parse_money(row[overseas_col])
            if domestic_col and domestic_col < len(row):
                ts.domestic_expense_10k = _parse_money(row[domestic_col])

            if ts.total_10k > 0:
                results.append(ts)

    return results


# ── 취업규칙 PDF/HWP 파서 ─────────────────────────────────────────────

@dataclass
class LeavePolicy:
    company_name: str
    source_file: str = ""

    # 연차
    annual_leave_min: int = 15         # 연차 최소 (1~2년차)
    annual_leave_max: int = 25         # 연차 최대 (20년 이상)
    annual_leave_note: str = ""

    # 여름 휴가
    summer_leave_days: int = 0
    summer_leave_note: str = ""

    # 병가
    sick_paid_days: int = 0           # 유급 병가
    sick_unpaid_days: int = 0         # 무급 병가 (추가)

    # 육아휴직
    parental_leave_months: int = 12
    parental_leave_note: str = ""

    # 특별 / 경조 휴가
    marriage_days: int = 5
    bereavement_days: int = 5
    childbirth_days: int = 90         # 출산휴가

    # 특수 제도
    study_leave: bool = False          # 학습휴직
    career_break: bool = False         # 생활안정휴직
    overseas_leave: bool = False       # 해외동반휴직

    # 근무 유연성
    flexible_work: bool = False
    flexible_note: str = ""
    remote_work: bool = False
    remote_note: str = ""

    # 해외연수
    overseas_training: bool = False
    overseas_training_note: str = ""
    language_training: bool = False
    mba_support: bool = False


# 취업규칙 조항 파싱을 위한 섹션 키워드
SECTION_PATTERNS = {
    "연차":   r"연\s*차\s*유\s*급\s*휴\s*가|제\s*\d+\s*조.*?연\s*차",
    "여름휴가": r"하\s*계\s*휴\s*가|여\s*름\s*휴\s*가|하\s*기\s*휴\s*가",
    "병가":   r"병\s*가",
    "육아휴직": r"육\s*아\s*휴\s*직",
    "경조휴가": r"경\s*조\s*사\s*휴\s*가|특\s*별\s*휴\s*가",
    "유연근무": r"유\s*연\s*근\s*무|탄\s*력\s*근\s*무|선\s*택\s*근\s*무",
    "재택근무": r"재\s*택\s*근\s*무|원\s*격\s*근\s*무",
    "해외연수": r"해\s*외\s*연\s*수|해\s*외\s*파\s*견|국\s*외\s*훈\s*련",
    "어학연수": r"어\s*학\s*연\s*수|어\s*학\s*지\s*원",
    "MBA":    r"MBA|학\s*위\s*과\s*정|위\s*탁\s*교\s*육",
    "학습휴직": r"학\s*습\s*휴\s*직|자\s*기\s*계\s*발\s*휴\s*직",
    "생활안정휴직": r"생\s*활\s*안\s*정\s*휴\s*직|리\s*프\s*레\s*시",
}


def parse_leave_policy(text: str, company_name: str, source_file: str = "") -> LeavePolicy:
    """취업규칙 텍스트 → 휴가/복지 정책 파싱"""
    policy = LeavePolicy(company_name=company_name, source_file=source_file)

    # 연차 일수 추출
    annual = _extract_annual_leave(text)
    if annual:
        policy.annual_leave_min, policy.annual_leave_max = annual
        policy.annual_leave_note = _extract_context(text, "연차유급휴가", chars=100)

    # 여름휴가
    summer = _extract_days(text, r"하계\s*휴가[^.]{0,50}?(\d+)\s*일")
    if summer:
        policy.summer_leave_days = summer
        policy.summer_leave_note = _extract_context(text, "하계휴가", chars=80)

    # 병가
    sick_paid = _extract_days(text, r"유급\s*병가[^.]{0,50}?(\d+)\s*(?:일|근무일)")
    if sick_paid:
        policy.sick_paid_days = sick_paid
    sick_unpaid = _extract_days(text, r"무급\s*병가[^.]{0,50}?(\d+)\s*(?:일|근무일)")
    if sick_unpaid:
        policy.sick_unpaid_days = sick_unpaid

    # 육아휴직 기간
    parental = _extract_days(text, r"육아\s*휴직[^.]{0,80}?(\d+)\s*(?:년|개월)", unit="month")
    if parental:
        policy.parental_leave_months = parental
        policy.parental_leave_note = _extract_context(text, "육아휴직", chars=120)

    # 경조휴가
    marriage = _extract_days(text, r"결혼[^.]{0,30}?(\d+)\s*일")
    if marriage:
        policy.marriage_days = marriage
    bereavement = _extract_days(text, r"(?:부모|배우자)[^.]{0,30}?사망[^.]{0,30}?(\d+)\s*일")
    if bereavement:
        policy.bereavement_days = bereavement

    # 불린 플래그
    policy.flexible_work = bool(re.search(SECTION_PATTERNS["유연근무"], text))
    policy.flexible_note = _extract_context(text, "유연근무", chars=150) if policy.flexible_work else ""

    policy.remote_work = bool(re.search(SECTION_PATTERNS["재택근무"], text))
    policy.remote_note = _extract_context(text, "재택근무", chars=150) if policy.remote_work else ""

    policy.overseas_training = bool(re.search(SECTION_PATTERNS["해외연수"], text))
    policy.overseas_training_note = _extract_context(text, "해외연수", chars=200) if policy.overseas_training else ""

    policy.language_training = bool(re.search(SECTION_PATTERNS["어학연수"], text))
    policy.mba_support = bool(re.search(SECTION_PATTERNS["MBA"], text))
    policy.study_leave = bool(re.search(SECTION_PATTERNS["학습휴직"], text))
    policy.career_break = bool(re.search(SECTION_PATTERNS["생활안정휴직"], text))
    policy.overseas_leave = bool(re.search(r"해외\s*동반\s*휴직|가족\s*동반\s*휴직", text))

    return policy


def _extract_annual_leave(text: str):
    """연차 일수 범위 (최소, 최대) 추출"""
    # 패턴 1: "15일 이상 25일 이하"
    m = re.search(r"(\d+)\s*일\s*이상[^.]{0,30}?(\d+)\s*일\s*이하", text)
    if m:
        return int(m.group(1)), int(m.group(2))

    # 패턴 2: "최소 15일, 최대 25일"
    m = re.search(r"최소\s*(\d+)\s*일[^.]{0,20}?최대\s*(\d+)\s*일", text)
    if m:
        return int(m.group(1)), int(m.group(2))

    # 패턴 3: 연차 일수 테이블 패턴 "1년 미만 11일, ... 3년 이상 15일"
    mins = re.findall(r"연차[^.]{0,200}?(\d+)\s*일", text)
    if mins:
        days = [int(d) for d in mins if 5 <= int(d) <= 30]
        if days:
            return min(days), max(days)

    return None


def _extract_days(text: str, pattern: str, unit: str = "day") -> int:
    m = re.search(pattern, text)
    if not m:
        return 0
    val = int(m.group(1))
    if unit == "month":
        return val  # 개월 단위 그대로
    return val


def _extract_context(text: str, keyword: str, chars: int = 100) -> str:
    """키워드 주변 텍스트 추출"""
    idx = text.find(keyword)
    if idx < 0:
        return ""
    start = max(0, idx - 20)
    end = min(len(text), idx + chars)
    return text[start:end].replace("\n", " ").strip()


# ── 노동조합 공시 파서 ─────────────────────────────────────────────────

@dataclass
class UnionInfo:
    company_name: str
    year: int
    union_name: str = ""
    member_count: int = 0
    total_employees: int = 0
    union_rate_pct: float = 0


def parse_union_tables(company_name: str, tables: list) -> list[UnionInfo]:
    results = []
    for table in tables:
        if not table or len(table) < 2:
            continue
        header = [str(c).strip() for c in table[0]]
        year_col = _find_col(header, ["연도"])
        name_col = _find_col(header, ["노동조합명", "조합명"])
        member_col = _find_col(header, ["조합원수", "조합원"])
        rate_col = _find_col(header, ["가입률", "조직률"])

        for row in table[1:]:
            row = [str(c).strip() for c in row]
            year = _parse_year(row[year_col] if year_col is not None else row[0])
            if not year:
                continue
            ui = UnionInfo(company_name=company_name, year=year)
            if name_col and name_col < len(row):
                ui.union_name = row[name_col]
            if member_col and member_col < len(row):
                m = re.search(r"[\d,]+", row[member_col])
                ui.member_count = int(m.group().replace(",", "")) if m else 0
            if rate_col and rate_col < len(row):
                m = re.search(r"[\d.]+", row[rate_col])
                ui.union_rate_pct = float(m.group()) if m else 0
            results.append(ui)

    return results


# ── 통합 분석 ──────────────────────────────────────────────────────────

def analyze_crawled_data(company_name: str, crawled: dict) -> dict:
    """crawl_company() 결과 → 구조화된 분석 결과"""
    disclosures = crawled.get("disclosures", {})
    result = {"company": company_name}

    # 복리후생비
    welfare_tables = disclosures.get("복리후생비", {}).get("tables", [])
    welfare = parse_welfare_tables(company_name, [r for t in welfare_tables for r in (t,)])
    if welfare:
        result["welfare"] = [asdict(w) for w in welfare[:3]]  # 최근 3년

    # 교육훈련비
    training_tables = disclosures.get("교육훈련비", {}).get("tables", [])
    training = parse_training_tables(company_name, [r for t in training_tables for r in (t,)])
    if training:
        result["training"] = [asdict(t) for t in training[:3]]

    # 노동조합
    union_tables = disclosures.get("노동조합", {}).get("tables", [])
    union = parse_union_tables(company_name, [r for t in union_tables for r in (t,)])
    if union:
        latest_union = union[0]
        result["union"] = asdict(latest_union)

    return result


def extract_leave_from_file(file_path: str, company_name: str) -> Optional[LeavePolicy]:
    """다운로드된 취업규칙 파일에서 휴가 정책 추출"""
    from pathlib import Path
    ext = Path(file_path).suffix.lower()

    text = ""
    if ext == ".pdf":
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        except Exception as e:
            logger.error(f"PDF 읽기 실패: {e}")
    elif ext in (".hwp", ".hwpx"):
        from .regulation_parser import _extract_hwp_text
        text = _extract_hwp_text(file_path)

    if not text:
        return None
    return parse_leave_policy(text, company_name, source_file=file_path)


# ── 유틸 ──────────────────────────────────────────────────────────────

def _find_col(header: list, keywords: list) -> Optional[int]:
    for i, h in enumerate(header):
        if any(kw in h for kw in keywords):
            return i
    return None


def _parse_year(s: str) -> int:
    m = re.search(r"20\d{2}", s)
    return int(m.group()) if m else 0


def _parse_money(s: str) -> float:
    """금액 문자열 → 만원 단위"""
    s = s.replace(",", "").strip()
    m = re.search(r"[\d.]+", s)
    if not m:
        return 0
    val = float(m.group())
    # 원 단위 변환
    if val >= 1_000_000:
        return round(val / 10000, 1)
    elif val >= 10000:
        return round(val / 10000, 1)
    return round(val, 1)


def _map_welfare_field(header_text: str) -> Optional[str]:
    for kw, field in WELFARE_FIELD_MAP.items():
        if kw in header_text:
            return field
    return None


def _any_field_set(ws: WelfareSummary) -> bool:
    return any([
        ws.meal_10k, ws.transport_10k, ws.medical_10k,
        ws.childcare_tuition_10k, ws.housing_loan_10k,
        ws.recreation_10k, ws.welfare_point_10k,
    ])
