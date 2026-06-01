import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { PALETTE, W } from "../theme";
import { DeepDiveProps } from "../lib/format";
import { ensureFonts } from "../load-fonts";

export const CompanyProfileScene: React.FC<DeepDiveProps> = (props) => {
  ensureFonts();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 16 });

  const asset = props.asset || {};
  const blind = props.blind || {};

  const totalAssets100m = asset.total_assets_100m || 0;
  const assetRank = asset.asset_rank || 0;

  // 억원 → 조 표기
  const assetStr = totalAssets100m >= 10000
    ? `${Math.round(totalAssets100m / 10000).toLocaleString()}조원`
    : totalAssets100m > 0 ? `${totalAssets100m.toLocaleString()}억원` : "—";

  const blindScores = [
    { label: "종합 평점", value: blind.overall || 0, max: 5, highlight: true },
    { label: "급여·복지", value: blind.salary_benefit || 0, max: 5 },
    { label: "워라밸", value: blind.work_life || 0, max: 5 },
    { label: "사내문화", value: blind.culture || 0, max: 5 },
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
          기업 규모 · 블라인드 평점
        </div>
      </div>

      {/* 카드 컨테이너 */}
      <div style={{
        position: "absolute",
        left: 60, top: 120, right: 60, bottom: 60,
        display: "flex",
        gap: 36,
        opacity: enter,
        transform: `translateY(${(1 - enter) * 24}px)`,
      }}>
        {/* 왼쪽: 자산 규모 */}
        <div style={{
          flex: 1,
          background: "#1a1a1a",
          borderRadius: 12,
          padding: "44px 48px",
          borderLeft: `6px solid ${props.brandColor}`,
        }}>
          <div style={{ fontSize: 26, fontWeight: W.semibold, color: PALETTE.gray, letterSpacing: 2, marginBottom: 36 }}>
            자산 & 규모
          </div>

          <div style={{ marginBottom: 36 }}>
            <div style={{ fontSize: 22, color: PALETTE.gray, marginBottom: 6 }}>자산총계</div>
            <div style={{ fontSize: 64, fontWeight: W.black, color: PALETTE.white, letterSpacing: -2 }}>
              {assetStr}
            </div>
          </div>

          {assetRank > 0 && (
            <div style={{ marginBottom: 28 }}>
              <div style={{ fontSize: 22, color: PALETTE.gray, marginBottom: 6 }}>공공기관 자산순위</div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                <span style={{ fontSize: 52, fontWeight: W.black, color: PALETTE.warmGold }}>{assetRank}</span>
                <span style={{ fontSize: 30, color: PALETTE.gray }}>위</span>
              </div>
            </div>
          )}

          <div style={{
            marginTop: 24,
            padding: "14px 20px",
            background: "#111",
            borderRadius: 8,
            fontSize: 22,
            color: "#555",
          }}>
            출처: 알리오 공공기관 경영정보 공개시스템
          </div>
        </div>

        {/* 오른쪽: 블라인드 평점 */}
        <div style={{
          flex: 1,
          background: "#1a1a1a",
          borderRadius: 12,
          padding: "44px 48px",
          borderLeft: `6px solid ${PALETTE.warmGold}`,
        }}>
          <div style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            marginBottom: 36,
          }}>
            <div style={{ fontSize: 26, fontWeight: W.semibold, color: PALETTE.gray, letterSpacing: 2 }}>
              블라인드 평점
            </div>
            {(blind.review_count || 0) > 0 && (
              <div style={{ fontSize: 22, color: "#555" }}>
                리뷰 {(blind.review_count || 0).toLocaleString()}개
              </div>
            )}
          </div>

          {blindScores.map(({ label, value, max, highlight }, i) => {
            const barProgress = interpolate(
              frame,
              [10 + i * 7, 28 + i * 7],
              [0, value / max],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );
            return (
              <div key={label} style={{ marginBottom: 28 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                  <span style={{ fontSize: highlight ? 30 : 26, fontWeight: highlight ? W.bold : W.semibold, color: PALETTE.white }}>
                    {label}
                  </span>
                  <span style={{ fontSize: highlight ? 34 : 28, fontWeight: W.bold, color: highlight ? PALETTE.warmGold : PALETTE.gray }}>
                    {value > 0 ? value.toFixed(1) : "—"}<span style={{ fontSize: 20, color: "#555" }}>/5.0</span>
                  </span>
                </div>
                <div style={{ height: highlight ? 12 : 8, background: "#2a2a2a", borderRadius: 4 }}>
                  <div style={{
                    height: "100%",
                    width: `${barProgress * 100}%`,
                    background: highlight ? PALETTE.warmGold : props.brandColor,
                    borderRadius: 4,
                  }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
