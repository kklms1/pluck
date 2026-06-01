"""
보수규정 PDF/HWP 파서
- 호봉 테이블(직급 × 호봉 = 기본급) 추출
- 수당 항목 추출
- 한전 보수규정 실제 구조 기반
"""

import re
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# 직급명 정규화 맵 (기관마다 다른 직급명 → 표준화)
GRADE_NORMALIZE = {
    # 숫자형
    "1급": "1급", "2급": "2급", "3급": "3급",
    "4급": "4급", "5급": "5급", "6급": "6급", "7급": "7급",
    # 이름형 (한전식)
    "1직급": "1급", "2직급": "2급", "3직급": "3급",
    "4직급": "4급", "5직급": "5급", "6직급": "6급",
    "가급": "1급", "나급": "2급", "다급": "3급",
    "라급": "4급", "마급": "5급",
    # 직책형
    "부장": "2급", "차장": "3급", "과장": "4급",
    "대리": "5급", "주임": "5급", "사원": "6급",
    "수석": "2급", "선임": "4급", "책임": "3급",
    # 한전 직급
    "1E": "1급", "2E": "2급", "3E": "3급",
    "4E": "4급", "5E": "5급", "6E": "6급",
}

# 수당 키워드 → 표준명
ALLOWANCE_KEYWORDS = {
    "직급보조비": "직급보조비",
    "직무급": "직무급",
    "가족수당": "가족수당",
    "자녀수당": "가족수당",
    "명절상여": "명절상여",
    "정근수당": "정근수당",
    "시간외수당": "시간외수당",
    "연장근로": "시간외수당",
    "야간수당": "야간수당",
    "휴일수당": "휴일수당",
    "식대": "식대",
    "식비": "식대",
    "교통비": "교통비",
    "통근비": "교통비",
    "직책수당": "직책수당",
    "관리업무수당": "관리업무수당",
    "성과급": "성과급",
    "경영성과급": "성과급",
    "복지포인트": "복지포인트",
    "자기계발비": "자기계발비",
}


@dataclass
class HobongRow:
    grade: str          # 직급 (정규화)
    hobong: int         # 호봉
    base_salary: int    # 기본급 (만원, 100원 단위 → 만원 변환)


@dataclass
class ParsedSalaryTable:
    company_name: str
    source_file: str
    hobong_rows: list[HobongRow] = field(default_factory=list)
    # 고정 수당: 월 절대 금액 (만원). 예: {"식대": 14, "교통비": 8}
    allowances: dict[str, float] = field(default_factory=dict)
    # 기본급 비례 수당: 연간 배수. 예: {"성과급": 3.0, "명절상여": 2.0}
    # → 월 환산 = base_salary × ratio / 12
    allowance_ratios: dict[str, float] = field(default_factory=dict)
    parse_quality: float = 0.0
    notes: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────
# PDF 파서
# ─────────────────────────────────────────────────────────────

def parse_pdf(file_path: str, company_name: str) -> ParsedSalaryTable:
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pip install pdfplumber")

    result = ParsedSalaryTable(company_name=company_name, source_file=file_path)

    with pdfplumber.open(file_path) as pdf:
        logger.info(f"PDF {len(pdf.pages)}페이지 처리 중: {Path(file_path).name}")

        for page_num, page in enumerate(pdf.pages, 1):
            # 테이블 추출 시도
            tables = page.extract_tables()
            for table in tables:
                rows = _parse_table_rows(table)
                if rows:
                    result.hobong_rows.extend(rows)
                    logger.info(f"  p{page_num}: 호봉행 {len(rows)}개 추출")

            # 텍스트에서 수당 추출
            text = page.extract_text() or ""
            allowances = _extract_allowances_from_text(text)
            result.allowances.update(allowances)

            # 텍스트 기반 호봉 테이블 파싱 (테이블 추출 실패 시 폴백)
            if not tables:
                text_rows = _parse_hobong_from_text(text)
                result.hobong_rows.extend(text_rows)

    result.parse_quality = _calc_quality(result)
    logger.info(f"  파싱 완료: 호봉행 {len(result.hobong_rows)}개, "
                f"수당 {len(result.allowances)}개, 신뢰도 {result.parse_quality:.0%}")
    return result


def _parse_table_rows(table: list) -> list[HobongRow]:
    """pdfplumber 테이블에서 호봉행 추출"""
    if not table or len(table) < 2:
        return []

    rows = []
    header = [str(c).strip() if c else "" for c in table[0]]

    # 헤더에서 직급/호봉 컬럼 위치 파악
    grade_col = _find_col(header, ["직급", "직종", "등급", "구분"])
    hobong_col = _find_col(header, ["호봉", "호"])
    salary_col = _find_col(header, ["기본급", "기준급", "본봉", "봉급", "급여"])

    # 헤더가 직급행인 경우 (열: 직급, 1호봉, 2호봉, ...)
    if grade_col is not None and hobong_col is None:
        # 컬럼 헤더가 호봉 번호인 패턴
        hobong_cols = {}
        for i, h in enumerate(header):
            m = re.match(r"(\d+)\s*호봉?", h)
            if m:
                hobong_cols[i] = int(m.group(1))

        if hobong_cols:
            for data_row in table[1:]:
                if not data_row or not data_row[grade_col]:
                    continue
                grade_raw = str(data_row[grade_col]).strip()
                grade = _normalize_grade(grade_raw)
                if not grade:
                    continue
                for col_idx, hobong_num in hobong_cols.items():
                    if col_idx < len(data_row) and data_row[col_idx]:
                        salary = _parse_salary_value(str(data_row[col_idx]))
                        if salary > 0:
                            rows.append(HobongRow(grade=grade, hobong=hobong_num, base_salary=salary))
            return rows

    # 컬럼: 직급 | 호봉 | 기본급
    if grade_col is not None and hobong_col is not None and salary_col is not None:
        for data_row in table[1:]:
            if len(data_row) <= max(grade_col, hobong_col, salary_col):
                continue
            grade_raw = str(data_row[grade_col] or "").strip()
            hobong_raw = str(data_row[hobong_col] or "").strip()
            salary_raw = str(data_row[salary_col] or "").strip()

            grade = _normalize_grade(grade_raw)
            hobong = _parse_int(hobong_raw)
            salary = _parse_salary_value(salary_raw)

            if grade and hobong > 0 and salary > 0:
                rows.append(HobongRow(grade=grade, hobong=hobong, base_salary=salary))

    return rows


def _parse_hobong_from_text(text: str) -> list[HobongRow]:
    """텍스트에서 호봉 패턴 직접 파싱 (테이블 추출 실패 시 폴백)"""
    rows = []

    # 패턴: "6급 1호봉 2,150,000" 또는 "6급  1  2,150,000"
    pattern1 = re.compile(
        r"([가-힣0-9]+급|[가-힣]+직급|[0-9]+E)\s+"
        r"(\d{1,2})\s*호봉?\s+"
        r"([\d,]+(?:\.\d+)?)\s*원?"
    )
    for m in pattern1.finditer(text):
        grade = _normalize_grade(m.group(1))
        hobong = int(m.group(2))
        salary = _parse_salary_value(m.group(3))
        if grade and hobong > 0 and salary > 0:
            rows.append(HobongRow(grade=grade, hobong=hobong, base_salary=salary))

    return rows


def _extract_allowances_from_text(text: str) -> dict[str, int]:
    """텍스트에서 수당 금액 추출"""
    result = {}

    # 패턴: "식대 월 100,000원" 또는 "교통비: 80,000원"
    for keyword, std_name in ALLOWANCE_KEYWORDS.items():
        pattern = re.compile(
            rf"{keyword}[^\n]{{0,30}}?"
            r"([\d,]+(?:\.\d+)?)\s*(?:천원|만원|원)",
            re.IGNORECASE
        )
        for m in pattern.finditer(text):
            raw = m.group(1).replace(",", "")
            full_match = m.group(0)

            try:
                amount = float(raw)
                if "천원" in full_match:
                    amount = amount * 1000
                elif "만원" in full_match:
                    amount = amount * 10000
                # 원 단위 → 만원 변환
                if amount >= 10000:
                    amount = amount / 10000
                if 0 < amount < 1000:  # 합리적 범위 (만원 단위)
                    result[std_name] = round(amount, 1)
                    break
            except ValueError:
                continue

    return result


# ─────────────────────────────────────────────────────────────
# HWP 파서
# ─────────────────────────────────────────────────────────────

def parse_hwp(file_path: str, company_name: str) -> ParsedSalaryTable:
    """HWP 파일 파싱 (텍스트 추출 후 패턴 매칭)"""
    result = ParsedSalaryTable(company_name=company_name, source_file=file_path)

    text = _extract_hwp_text(file_path)
    if not text:
        result.notes.append("HWP 텍스트 추출 실패 - olefile 또는 python-hwp 필요")
        return result

    result.hobong_rows = _parse_hobong_from_text(text)
    result.allowances = _extract_allowances_from_text(text)
    result.parse_quality = _calc_quality(result)
    return result


def _extract_hwp_text(file_path: str) -> str:
    """HWP에서 텍스트 추출 (여러 방법 시도)"""
    # 방법 1: olefile 기반 직접 추출
    try:
        import olefile
        import zlib
        import struct

        with olefile.OleFileIO(file_path) as f:
            if f.exists("BodyText/Section0"):
                raw = f.openstream("BodyText/Section0").read()
                try:
                    text = zlib.decompress(raw, -15).decode("utf-16-le", errors="ignore")
                    return text
                except Exception:
                    pass
    except Exception:
        pass

    # 방법 2: hwp5txt (pip install hwp5)
    try:
        import subprocess
        result = subprocess.run(
            ["hwp5txt", file_path],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass

    logger.warning(f"HWP 텍스트 추출 실패: {file_path}")
    return ""


# ─────────────────────────────────────────────────────────────
# 유틸리티
# ─────────────────────────────────────────────────────────────

def parse_regulation_file(file_path: str, company_name: str) -> ParsedSalaryTable:
    """파일 확장자에 따라 적절한 파서 호출"""
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        return parse_pdf(file_path, company_name)
    elif ext in (".hwp", ".hwpx"):
        return parse_hwp(file_path, company_name)
    else:
        logger.warning(f"지원하지 않는 파일 형식: {ext}")
        return ParsedSalaryTable(company_name=company_name, source_file=file_path)


def _find_col(header: list[str], keywords: list[str]) -> Optional[int]:
    for i, h in enumerate(header):
        if any(kw in h for kw in keywords):
            return i
    return None


def _normalize_grade(raw: str) -> str:
    raw = raw.strip()
    # 직접 매핑
    if raw in GRADE_NORMALIZE:
        return GRADE_NORMALIZE[raw]
    # 패턴 매핑: "제6급" → "6급"
    m = re.match(r"제?([1-9])급", raw)
    if m:
        return f"{m.group(1)}급"
    m = re.match(r"([1-9])직급", raw)
    if m:
        return f"{m.group(1)}급"
    return ""


def _parse_salary_value(raw: str) -> int:
    """급여 문자열 → 만원 단위 정수"""
    clean = re.sub(r"[^\d.]", "", raw)
    if not clean:
        return 0
    try:
        val = float(clean)
        # 원 단위 (예: 2,150,000)
        if val >= 100000:
            return round(val / 10000)
        # 이미 만원 단위 (예: 215)
        elif val >= 100:
            return round(val)
        return 0
    except ValueError:
        return 0


def _parse_int(raw: str) -> int:
    m = re.search(r"\d+", raw)
    return int(m.group()) if m else 0


def _calc_quality(result: ParsedSalaryTable) -> float:
    score = 0.0
    if len(result.hobong_rows) >= 30:
        score += 0.6
    elif len(result.hobong_rows) >= 10:
        score += 0.4
    elif len(result.hobong_rows) > 0:
        score += 0.2
    if len(result.allowances) >= 5:
        score += 0.3
    elif len(result.allowances) > 0:
        score += 0.15
    return min(score, 1.0)
