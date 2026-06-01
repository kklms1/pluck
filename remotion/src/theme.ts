/**
 * 디자인 시스템 — 공기업 연봉 딥다이브
 * 컨셉: 프리미엄 금융 다크 (딥네이비 + 네온그린 실수령 + 골드 강조)
 */

export const PALETTE = {
  bgTop: "#0b1020",
  bgBottom: "#161f38",
  card: "rgba(255,255,255,0.045)",
  cardBorder: "rgba(255,255,255,0.09)",
  white: "#f5f7fb",
  gray: "#9aa6bf",
  dim: "#64718f",
  net: "#34f5a3", // 월 실수령 네온그린
  netGlow: "rgba(52,245,163,0.5)",
  gold: "#ffc83c", // 강조/마일스톤
  danger: "#ff6b6b", // 순환 잦음 등 경고
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

export function bgGradient(brand: string) {
  return `radial-gradient(1200px 700px at 78% 12%, ${hexA(
    brand,
    0.18
  )} 0%, rgba(0,0,0,0) 60%), linear-gradient(160deg, ${PALETTE.bgTop} 0%, ${PALETTE.bgBottom} 100%)`;
}
