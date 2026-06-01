import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { PALETTE, W } from "../theme";
import { DeepDiveProps } from "../lib/format";
import { ensureFonts } from "../load-fonts";

export const LocationScene: React.FC<DeepDiveProps> = (props) => {
  ensureFonts();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 16 });

  const loc = props.location || {};

  // 순환근무 강도에 따른 색상
  const rotationAccent =
    loc.rotation === "전국순환" ? PALETTE.marker
    : loc.rotation === "권역순환" ? PALETTE.warmGold
    : "#34c759"; // 본사상주

  const rows = [
    {
      icon: "📍",
      label: "본사 위치",
      main: loc.region ? `${loc.region}` : "—",
      sub: loc.hq_address || "",
      accent: props.brandColor,
    },
    {
      icon: loc.relocated ? "🏗️" : "🏢",
      label: "지방이전",
      main: loc.relocated
        ? `이전 완료 — ${loc.innovation_city || "혁신도시"}`
        : "해당 없음 (현 위치 유지)",
      sub: loc.relocated ? "혁신도시 이전 공공기관" : "",
      accent: loc.relocated ? PALETTE.warmGold : "#555",
    },
    {
      icon: "🔄",
      label: "순환근무",
      main: loc.rotation || "정보 없음",
      sub: loc.rotation_note || "",
      accent: rotationAccent,
    },
  ];

  return (
    <AbsoluteFill style={{
      background: PALETTE.ink,
      fontFamily: "Pretendard",
      color: PALETTE.white,
    }}>
      {/* 브랜드 세로막대 */}
      <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 10, background: props.brandColor }} />

      {/* 헤더 */}
      <div style={{ position: "absolute", top: 52, left: 60, display: "flex", alignItems: "baseline", gap: 24 }}>
        <div style={{ fontSize: 38, fontWeight: W.bold, color: props.brandColor, letterSpacing: 3 }}>
          {props.company}
        </div>
        <div style={{ fontSize: 30, fontWeight: W.semibold, color: PALETTE.gray, letterSpacing: 2 }}>
          본사 위치 · 근무형태
        </div>
      </div>

      {/* 근무지 카드 리스트 */}
      <div style={{
        position: "absolute",
        left: 60, top: 128, right: 60, bottom: 60,
        display: "flex",
        flexDirection: "column",
        gap: 24,
        opacity: enter,
        transform: `translateY(${(1 - enter) * 24}px)`,
      }}>
        {rows.map(({ icon, label, main, sub, accent }, i) => {
          const rowOp = interpolate(frame, [6 + i * 8, 20 + i * 8], [0, 1], {
            extrapolateLeft: "clamp", extrapolateRight: "clamp",
          });
          return (
            <div key={label} style={{
              display: "flex",
              alignItems: "center",
              gap: 32,
              padding: "32px 40px",
              background: "#1a1a1a",
              borderRadius: 12,
              borderLeft: `6px solid ${accent}`,
              opacity: rowOp,
              transform: `translateX(${(1 - rowOp) * 20}px)`,
            }}>
              <div style={{ fontSize: 52, flexShrink: 0, lineHeight: 1 }}>{icon}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 24, color: PALETTE.gray, marginBottom: 6, letterSpacing: 1 }}>
                  {label}
                </div>
                <div style={{ fontSize: 44, fontWeight: W.bold, color: PALETTE.white, lineHeight: 1.1 }}>
                  {main}
                </div>
                {sub && (
                  <div style={{ fontSize: 26, color: "#666", marginTop: 6 }}>{sub}</div>
                )}
              </div>

              {/* 순환근무 위험도 배지 */}
              {label === "순환근무" && loc.rotation && (
                <div style={{
                  padding: "8px 22px",
                  borderRadius: 6,
                  border: `2.5px solid ${accent}`,
                  fontSize: 26,
                  fontWeight: W.bold,
                  color: accent,
                  flexShrink: 0,
                  letterSpacing: 1,
                }}>
                  {loc.rotation === "전국순환" ? "⚠ 전국발령" : loc.rotation === "권역순환" ? "권역내" : "본사"}
                </div>
              )}
            </div>
          );
        })}

        {/* 하단 노트 */}
        {loc.branch_scope && (
          <div style={{ fontSize: 24, color: "#555", paddingLeft: 8, marginTop: 4 }}>
            ※ {loc.branch_scope}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
