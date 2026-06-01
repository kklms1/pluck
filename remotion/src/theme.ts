/**
 * 디자인 시스템 — 공기업 연봉 딥다이브
 * 컨셉: 정보 채널 — 진짜 사람이 만든 느낌 (굵은 활자 + 형광펜 + 빨간 동그라미)
 */

export const PALETTE = {
  // 배경
  ink: "#111111",        // 메인 다크 배경 (그라디언트 없는 단색)
  inkSoft: "#1a1a1a",
  cream: "#faf8f0",      // 문서/종이 느낌 배경
  // 텍스트
  white: "#f5f5f5",
  offWhite: "#e8e6e0",
  gray: "#888888",
  dim: "#555555",
  // 사람 손맛 강조색
  highlight: "#ffe432",  // 형광펜 노랑
  marker: "#e53e3e",     // 빨간 펜
  warmGold: "#f5c842",   // 골드 (글로우 없이도 눈에 띄는 채도)
  // 하위호환 (SalaryScene 등에서 사용)
  card: "rgba(255,255,255,0.045)",
  cardBorder: "rgba(255,255,255,0.09)",
  net: "#34f5a3",
  netGlow: "rgba(52,245,163,0.5)",
  gold: "#ffc83c",
  danger: "#e53e3e",
  brandDefault: "#3aa0ff",
};

export const FONT = { family: "Pretendard" };

export const W = {
  regular: 400,
  medium: 500,
  semibold: 600,
  bold: 700,
  extrabold: 800,
  black: 900,
};

export function hexA(hex: string, a: number) {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
}

// bgGradient 제거됨 — 모든 씬이 PALETTE.ink 단색 배경 사용
