import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { PALETTE, W } from "../theme";
import { DeepDiveProps } from "../lib/format";
import { ensureFonts } from "../load-fonts";

const ITEMS = [
  { icon: "🏠", label: "주거지원", desc: "사택 · 기숙사 · 주택자금 대출" },
  { icon: "🏥", label: "의료지원", desc: "건강검진 · 의료비 · 실손보험" },
  { icon: "🎓", label: "자기개발", desc: "학비지원 · 자격증 · 외국어연수" },
  { icon: "🚗", label: "교통지원", desc: "통근버스 · 주차 · 교통비" },
  { icon: "🍽️", label: "식비", desc: "구내식당 · 식대 월정액" },
  { icon: "👶", label: "가족지원", desc: "육아휴직 · 어린이집 · 가족수당" },
];

export const WelfareScene: React.FC<DeepDiveProps> = (props) => {
  ensureFonts();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 16 });

  const welfare = props.welfare || {};
  const totalPerPerson = welfare.total_per_person_10k || 0;

  return (
    <AbsoluteFill style={{
      background: PALETTE.ink,
      fontFamily: "Pretendard",
      color: PALETTE.white,
    }}>
      {/* 브랜드 세로막대 */}
      <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 10, background: props.brandColor }} />

      {/* 헤더 */}
      <div style={{
        position: "absolute",
        top: 52, left: 60,
        display: "flex", alignItems: "center", gap: 24,
      }}>
        <div style={{ fontSize: 38, fontWeight: W.bold, color: props.brandColor, letterSpacing: 3 }}>
          {props.company} — 복리후생
        </div>
        {totalPerPerson > 0 && (
          <div style={{
            background: PALETTE.highlight,
            color: "#111",
            padding: "6px 18px",
            borderRadius: 5,
            fontSize: 28,
            fontWeight: W.extrabold,
          }}>
            1인당 연 {Math.round(totalPerPerson).toLocaleString()}만원
          </div>
        )}
      </div>

      {/* 6칸 그리드 */}
      <div style={{
        position: "absolute",
        left: 60, top: 130, right: 60, bottom: 56,
        display: "grid",
        gridTemplateColumns: "1fr 1fr 1fr",
        gridTemplateRows: "1fr 1fr",
        gap: 22,
        opacity: enter,
        transform: `translateY(${(1 - enter) * 20}px)`,
      }}>
        {ITEMS.map(({ icon, label, desc }, i) => {
          const itemOp = interpolate(frame, [8 + i * 5, 22 + i * 5], [0, 1], {
            extrapolateLeft: "clamp", extrapolateRight: "clamp",
          });
          return (
            <div key={label} style={{
              background: "#1a1a1a",
              borderRadius: 12,
              padding: "30px 32px",
              borderTop: `4px solid ${props.brandColor}`,
              opacity: itemOp,
              transform: `translateY(${(1 - itemOp) * 14}px)`,
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
            }}>
              <div style={{ fontSize: 44, marginBottom: 10, lineHeight: 1 }}>{icon}</div>
              <div style={{ fontSize: 30, fontWeight: W.bold, color: PALETTE.white, marginBottom: 6 }}>{label}</div>
              <div style={{ fontSize: 22, color: PALETTE.gray, lineHeight: 1.4 }}>{desc}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
