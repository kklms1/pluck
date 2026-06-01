import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { PALETTE, W, bgGradient, hexA } from "../theme";
import { CareerPoint, comma } from "../lib/format";
import { ensureFonts } from "../load-fonts";

/** 연차 카드 1장 (모션: 등장 스프링 + 숫자 카운트업 + 진행바) */
export const SalaryScene: React.FC<{
  point: CareerPoint;
  company: string;
  brandColor: string;
  total: number;
}> = ({ point, company, brandColor, total }) => {
  ensureFonts();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enter = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 18 });
  const countT = interpolate(frame, [0, 22], [0, 1], { extrapolateRight: "clamp" });

  const net = Math.round(point.monthly_net_10k * countT);
  const gross = Math.round(point.annual_gross_10k * countT);
  const progress = point.career_year / total;
  const isMilestone = point.career_year % 5 === 0;

  return (
    <AbsoluteFill style={{ background: bgGradient(brandColor), fontFamily: "Pretendard, sans-serif", color: PALETTE.white }}>
      {/* 기업 배지 */}
      <div style={{ position: "absolute", top: 48, left: 64, fontSize: 32, fontWeight: W.bold, color: brandColor }}>
        {company}
      </div>
      <div style={{ position: "absolute", top: 52, right: 72, fontSize: 30, fontWeight: W.semibold, color: PALETTE.dim }}>
        {point.career_year} / {total}
      </div>

      {/* 좌측: 연차 초대형 */}
      <div
        style={{
          position: "absolute",
          left: 90,
          top: 250,
          transform: `translateX(${(1 - enter) * -60}px)`,
          opacity: enter,
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline" }}>
          <span style={{ fontSize: 360, fontWeight: W.black, color: brandColor, lineHeight: 0.85, letterSpacing: -10 }}>
            {point.career_year}
          </span>
          <span style={{ fontSize: 90, fontWeight: W.bold, color: PALETTE.gray, marginLeft: 10 }}>년차</span>
        </div>
        <div style={{ display: "flex", gap: 16, marginTop: 30 }}>
          <Pill text={point.grade} brand={brandColor} />
          <Pill text={`${point.hobong}호봉`} muted />
        </div>
      </div>

      {/* 우측: 세전 + 실수령 */}
      <div style={{ position: "absolute", right: 90, top: 210, width: 760, textAlign: "right", opacity: enter }}>
        <div style={{ fontSize: 40, fontWeight: W.semibold, color: PALETTE.gray }}>세전 연봉</div>
        <div style={{ fontSize: 110, fontWeight: W.extrabold, color: PALETTE.white, letterSpacing: -2 }}>
          {comma(gross)}<span style={{ fontSize: 56, color: PALETTE.gray }}>만원</span>
        </div>

        <div style={{ height: 2, background: PALETTE.cardBorder, margin: "26px 0" }} />

        <div style={{ display: "inline-flex", alignItems: "center", gap: 14, padding: "8px 22px", borderRadius: 14, background: hexA(PALETTE.net, 0.14) }}>
          <span style={{ fontSize: 38, fontWeight: W.bold, color: PALETTE.net }}>월 실수령</span>
        </div>
        <div
          style={{
            fontSize: 200,
            fontWeight: W.black,
            color: PALETTE.net,
            lineHeight: 1,
            letterSpacing: -4,
            textShadow: `0 0 60px ${PALETTE.netGlow}`,
          }}
        >
          {net}<span style={{ fontSize: 80, fontWeight: W.extrabold }}>만원</span>
        </div>
        <div style={{ fontSize: 30, color: PALETTE.dim, marginTop: 10 }}>
          4대보험+소득세 공제율 {point.tax_rate_pct.toFixed(1)}%
        </div>
      </div>

      {isMilestone && (
        <div
          style={{
            position: "absolute",
            left: 90,
            top: 700,
            padding: "14px 28px",
            borderRadius: 14,
            background: hexA(PALETTE.gold, 0.16),
            border: `1.5px solid ${hexA(PALETTE.gold, 0.5)}`,
            fontSize: 36,
            fontWeight: W.bold,
            color: PALETTE.gold,
          }}
        >
          ★ {point.career_year}년차 마일스톤
        </div>
      )}

      {/* 진행바 */}
      <div style={{ position: "absolute", bottom: 0, left: 0, width: "100%", height: 8, background: hexA("#ffffff", 0.08) }}>
        <div style={{ width: `${progress * 100}%`, height: "100%", background: brandColor, boxShadow: `0 0 20px ${hexA(brandColor, 0.8)}` }} />
      </div>
    </AbsoluteFill>
  );
};

const Pill: React.FC<{ text: string; brand?: string; muted?: boolean }> = ({ text, brand, muted }) => (
  <div
    style={{
      padding: "14px 28px",
      borderRadius: 16,
      fontSize: 46,
      fontWeight: W.bold,
      color: muted ? PALETTE.gray : PALETTE.white,
      background: muted ? "rgba(255,255,255,0.05)" : hexA(brand || PALETTE.brandDefault, 0.2),
      border: `1.5px solid ${muted ? PALETTE.cardBorder : hexA(brand || PALETTE.brandDefault, 0.6)}`,
    }}
  >
    {text}
  </div>
);
