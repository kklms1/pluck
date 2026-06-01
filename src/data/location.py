"""
공기업 본사 위치 · 지방이전 · 순환/업무순환 데이터

공기업 취준생에게 연봉만큼 중요한 '근무지' 정보를 다룬다.
  - hq_address:   본사 주소
  - region:       광역 지역 (시/도)
  - relocated:    혁신도시 지방이전 대상/완료 여부
  - innovation_city: 이전한 혁신도시명 (없으면 "")
  - rotation:     순환근무 강도 (RotationLevel)
  - rotation_note: 순환 구체 설명 (전국/권역/본사상주 등)
  - branch_scope: 사업소·지사 분포 설명

데이터 출처: 각 기관 공시 기본정보 + 혁신도시 이전 고시 + 인사규정(전보·순환) 일반론.
실제 수치는 기관별로 변동될 수 있어 영상에서는 '참고용'으로 표기한다.
취업규칙/인사규정 파싱으로 보완 가능(parse_rotation_from_text).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Optional


# 순환근무 강도 (지방 취준생이 가장 궁금해하는 부분)
ROTATION_NATIONWIDE = "전국순환"     # 전국 사업소·지사로 발령
ROTATION_REGIONAL = "권역순환"       # 권역(예: 영남권) 내 순환
ROTATION_HQ_CENTRIC = "본사상주"     # 본사 위주, 순환 적음


@dataclass
class CompanyLocation:
    company_name: str
    hq_address: str
    region: str
    relocated: bool = False           # 지방이전(혁신도시) 여부
    innovation_city: str = ""         # 혁신도시명
    rotation: str = ROTATION_NATIONWIDE
    rotation_note: str = ""
    branch_scope: str = ""
    source: str = "curated"


# ── 큐레이션 데이터 (주요 공기업) ─────────────────────────────────────
LOCATIONS: dict[str, CompanyLocation] = {
    "한국전력공사": CompanyLocation(
        "한국전력공사", "전남 나주시 빛가람로 (빛가람혁신도시)", "전남",
        relocated=True, innovation_city="나주 빛가람혁신도시",
        rotation=ROTATION_NATIONWIDE,
        rotation_note="전국 사업소 순환근무, 입사 후 지역본부 배치 일반적",
        branch_scope="전국 지역본부·지사 200곳 이상",
    ),
    "한국수자원공사": CompanyLocation(
        "한국수자원공사", "대전 대덕구 (대덕연구단지)", "대전",
        relocated=False, innovation_city="",
        rotation=ROTATION_NATIONWIDE,
        rotation_note="본사 대전, 전국 댐·정수장·지사 순환",
        branch_scope="전국 유역·권역 사업장",
    ),
    "한국가스공사": CompanyLocation(
        "한국가스공사", "대구 동구 (대구신서혁신도시)", "대구",
        relocated=True, innovation_city="대구 신서혁신도시",
        rotation=ROTATION_NATIONWIDE,
        rotation_note="본사 대구, 전국 생산기지·공급관리소 순환",
        branch_scope="전국 생산기지·지역본부",
    ),
    "한국토지주택공사": CompanyLocation(
        "한국토지주택공사", "경남 진주시 (진주혁신도시)", "경남",
        relocated=True, innovation_city="진주혁신도시",
        rotation=ROTATION_NATIONWIDE,
        rotation_note="본사 진주, 전국 지역본부 순환(수도권 사업 비중 높음)",
        branch_scope="전국 지역본부",
    ),
    "국민건강보험공단": CompanyLocation(
        "국민건강보험공단", "강원 원주시 (원주혁신도시)", "강원",
        relocated=True, innovation_city="원주혁신도시",
        rotation=ROTATION_NATIONWIDE,
        rotation_note="본부 원주, 전국 지사 순환근무",
        branch_scope="전국 시·군 지사 178곳",
    ),
    "한국도로공사": CompanyLocation(
        "한국도로공사", "경북 김천시 (김천혁신도시)", "경북",
        relocated=True, innovation_city="김천혁신도시",
        rotation=ROTATION_NATIONWIDE,
        rotation_note="본사 김천, 전국 고속도로 지사·영업소 순환",
        branch_scope="전국 지역본부·지사",
    ),
    "한국철도공사": CompanyLocation(
        "한국철도공사", "대전 동구 (대전역 인근)", "대전",
        relocated=False, innovation_city="",
        rotation=ROTATION_NATIONWIDE,
        rotation_note="본사 대전, 전국 역·차량기지 순환(직렬별 상이)",
        branch_scope="전국 역·차량사업소",
    ),
    "한국공항공사": CompanyLocation(
        "한국공항공사", "서울 강서구 (김포공항)", "서울",
        relocated=False, innovation_city="",
        rotation=ROTATION_REGIONAL,
        rotation_note="전국 14개 공항 순환(김포·김해·제주 등)",
        branch_scope="전국 지방공항",
    ),
    "인천국제공항공사": CompanyLocation(
        "인천국제공항공사", "인천 중구 (영종도)", "인천",
        relocated=False, innovation_city="",
        rotation=ROTATION_HQ_CENTRIC,
        rotation_note="인천공항 단일 사업장 상주, 순환 부담 적음",
        branch_scope="인천국제공항 상주",
    ),
    "한국마사회": CompanyLocation(
        "한국마사회", "경기 과천시", "경기",
        relocated=False, innovation_city="",
        rotation=ROTATION_REGIONAL,
        rotation_note="서울·부산경남·제주 경마공원 및 지사 순환",
        branch_scope="경마공원·전국 지사",
    ),
    "국민연금공단": CompanyLocation(
        "국민연금공단", "전북 전주시 (전북혁신도시)", "전북",
        relocated=True, innovation_city="전북혁신도시",
        rotation=ROTATION_NATIONWIDE,
        rotation_note="본부 전주, 전국 지사 순환근무",
        branch_scope="전국 지역본부·지사",
    ),
    "근로복지공단": CompanyLocation(
        "근로복지공단", "울산 중구 (울산혁신도시)", "울산",
        relocated=True, innovation_city="울산혁신도시",
        rotation=ROTATION_NATIONWIDE,
        rotation_note="본부 울산, 전국 지사·병원 순환",
        branch_scope="전국 지사·산재병원",
    ),
    "한국원자력환경공단": CompanyLocation(
        "한국원자력환경공단", "경북 경주시", "경북",
        relocated=True, innovation_city="경주",
        rotation=ROTATION_HQ_CENTRIC,
        rotation_note="경주 본사·방폐장 상주 위주",
        branch_scope="경주 처분시설 중심",
    ),
    "한국환경공단": CompanyLocation(
        "한국환경공단", "인천 서구 (환경산업연구단지)", "인천",
        relocated=False, innovation_city="",
        rotation=ROTATION_REGIONAL,
        rotation_note="본사 인천, 전국 권역본부 순환",
        branch_scope="전국 권역·지사",
    ),
    "한국농어촌공사": CompanyLocation(
        "한국농어촌공사", "전남 나주시 (빛가람혁신도시)", "전남",
        relocated=True, innovation_city="나주 빛가람혁신도시",
        rotation=ROTATION_NATIONWIDE,
        rotation_note="본사 나주, 전국 지역본부·지사 순환",
        branch_scope="전국 지사 93곳",
    ),
}


def get_location(company_name: str) -> Optional[CompanyLocation]:
    return LOCATIONS.get(company_name)


def get_location_dict(company_name: str) -> dict:
    loc = LOCATIONS.get(company_name)
    return asdict(loc) if loc else {}


# ── 인사규정/취업규칙 텍스트 기반 순환근무 보완 파싱 ───────────────────
_NATIONWIDE_KW = ["전국", "전보", "타지역", "전국 사업소", "전국지사"]
_HQ_KW = ["본사 근무", "상주", "단일 사업장"]


def parse_rotation_from_text(text: str, company_name: str = "") -> dict:
    """
    인사규정/취업규칙 전문에서 순환·전보 관련 단서를 추출(보조).
    큐레이션 데이터가 우선이며, 없을 때 fallback으로 사용.
    """
    result = {"rotation": "", "rotation_note": "", "source": "parsed"}
    if not text:
        return result

    # 전보/순환 언급 빈도
    rotate_hits = len(re.findall(r"전보|순환근무|순환 근무|전출|전입", text))
    nationwide = any(kw in text for kw in _NATIONWIDE_KW)
    hq_only = any(kw in text for kw in _HQ_KW)

    if rotate_hits >= 1 and nationwide:
        result["rotation"] = ROTATION_NATIONWIDE
        result["rotation_note"] = "인사규정상 전보·순환근무 조항 존재 (전국 범위 추정)"
    elif rotate_hits >= 1:
        result["rotation"] = ROTATION_REGIONAL
        result["rotation_note"] = "인사규정상 전보·순환 조항 존재 (권역 추정)"
    elif hq_only:
        result["rotation"] = ROTATION_HQ_CENTRIC
        result["rotation_note"] = "본사·단일 사업장 상주 추정"

    return result


def format_location_summary(loc: CompanyLocation) -> str:
    """영상 자막/설명용 한 줄 요약"""
    moved = f"지방이전✅ {loc.innovation_city}" if loc.relocated else "수도권/현 위치 유지"
    return (f"본사: {loc.hq_address} · {moved} · "
            f"근무형태: {loc.rotation}({loc.rotation_note})")
