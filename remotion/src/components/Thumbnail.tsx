import { AbsoluteFill } from "remotion";
import { PALETTE, W, bgGradient, hexA } from "../theme";
import { DeepDiveProps, won, comma } from "../lib/format";
import { ensureFonts } from "../load-fonts";

/**
 * 메인 썸네일 (1280x720)
 * 후킹: "신입 실수령 XXX만 → 30년차 X.X억" + 호기심 갭
 */
export const Thumbnail: React.FC<DeepDiveProps> = (props) => {
  ensureFonts();
  const { company, brandColor, career } = props;
  const first = career[0];
  const last = career[career.length - 1];
  const net1 = Math.round(first.monthly_net_10k);
  const grossLast = won(last.annual_gross_10k);

  return (
    <AbsoluteFill
      style={{
        background: bgGradient(brandColor),
        fontFamily: "Pretendard, sans-serif",
        color: PALETTE.white,
        overflow: "hidden",
      }}
    >
      {/* 배경 초대형 워터마크 숫자 */}
      <div
        style={{
          position: "absolute",
          right: -60,
          top: -40,
          fontSize: 620,
          fontWeight: W.black,
          color: hexA(brandColor, 0.1),
          lineHeight: 1,
          letterSpacing: -20,
        }}
      >
        ₩
      </div>

      {/* 상단: 기업 배지 + 에브로우 */}
      <div style={{ position: "absolute", top: 54, left: 64, display: "flex", alignItems: "center", gap: 18 }}>
        <div
          style={{
            padding: "12px 26px",
            borderRadius: 999,
            border: `2px solid ${brandColor}`,
            background: hexA(brandColor, 0.14),
            fontSize: 34,
            fontWeight: W.bold,
            color: PALETTE.white,
          }}
        >
          {company}
        </div>
        <div style={{ fontSize: 28, fontWeight: W.semibold, color: PALETTE.gray, letterSpacing: 2 }}>
          연봉 딥다이브
        </div>
      </div>

      {/* 메인 카피 */}
      <div style={{ position: "absolute", left: 64, top: 150, display: "flex", flexDirection: "column" }}>
        <div style={{ fontSize: 46, fontWeight: W.bold, color: PALETTE.gray, marginBottom: 4 }}>
          신입 첫 달 <span style={{ color: PALETTE.white }}>실수령</span>
        </div>

        <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
          <span
            style={{
              fontSize: 230,
              fontWeight: W.black,
              color: PALETTE.net,
              lineHeight: 0.9,
              letterSpacing: -6,
              textShadow: `0 0 60px ${PALETTE.netGlow}`,
            }}
          >
            {net1}
          </span>
          <span style={{ fontSize: 76, fontWeight: W.extrabold, color: PALETTE.net }}>만원</span>
        </div>

        {/* 30년차 라인 */}
        <div style={{ display: "flex", alignItems: "center", gap: 18, marginTop: 14 }}>
          <span style={{ fontSize: 46, fontWeight: W.bold, color: PALETTE.gray }}>30년차엔</span>
          <span
            style={{
              fontSize: 84,
              fontWeight: W.black,
              color: PALETTE.gold,
              letterSpacing: -2,
              textShadow: `0 0 40px ${hexA(PALETTE.gold, 0.45)}`,
            }}
          >
            {grossLast}
          </span>
          <span style={{ fontSize: 46, fontWeight: W.bold, color: PALETTE.gray }}>까지</span>
        </div>
      </div>

      {/* 하단 후킹 태그 */}
      <div
        style={{
          position: "absolute",
          left: 64,
          bottom: 46,
          padding: "16px 30px",
          borderRadius: 16,
          background: hexA(brandColor, 0.18),
          border: `1.5px solid ${hexA(brandColor, 0.55)}`,
          fontSize: 38,
          fontWeight: W.extrabold,
          color: PALETTE.white,
        }}
      >
        호봉표 그대로 <span style={{ color: brandColor }}>전격 공개</span>
      </div>

      {/* 우하단 신뢰 배지 */}
      <div
        style={{
          position: "absolute",
          right: 56,
          bottom: 50,
          textAlign: "right",
          fontSize: 25,
          fontWeight: W.semibold,
          color: PALETTE.dim,
          lineHeight: 1.45,
        }}
      >
        세전 {comma(first.annual_gross_10k)}만 → {comma(last.annual_gross_10k)}만
        <br />
        알리오 보수규정 기준
      </div>

      {/* 비네팅 */}
      <AbsoluteFill
        style={{
          boxShadow: "inset 0 0 240px rgba(0,0,0,0.55)",
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};
