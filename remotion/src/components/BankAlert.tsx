import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { PALETTE, W, hexA } from "../theme";
import { DeepDiveProps, CareerPoint, comma } from "../lib/format";
import { ensureFonts } from "../load-fonts";

/**
 * 시그니처 후보 #1 — "통장 입금 알림"
 * 매 연차 실수령을 은행 푸시 알림 UI로 보여주는 우리만의 각인 장치.
 * 1년차 → 중간 → 30년차 알림이 순차로 쌓이며 성장 체감.
 */
const won = (man: number) => comma(man * 10000);

export const BankAlert: React.FC<DeepDiveProps> = (props) => {
  ensureFonts();
  const career = props.career || [];
  const pick = (y: number) =>
    career.find((p) => p.career_year === y) || career[Math.min(y, career.length - 1)];
  const picks = [pick(1), pick(15), pick(30)].filter(Boolean) as CareerPoint[];

  return (
    <AbsoluteFill
      style={{
        background:
          `radial-gradient(900px 600px at 50% 0%, ${hexA(props.brandColor, 0.35)} 0%, rgba(0,0,0,0) 55%),` +
          " linear-gradient(180deg,#04060c 0%,#0b1224 100%)",
        fontFamily: "Pretendard, sans-serif",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      {/* 상단 잠금화면 시계 느낌 */}
      <div style={{ position: "absolute", top: 70, width: "100%", textAlign: "center", color: "#fff", opacity: 0.85 }}>
        <div style={{ fontSize: 40, fontWeight: W.semibold, letterSpacing: 2 }}>오전 9:30</div>
        <div style={{ fontSize: 26, color: PALETTE.gray, marginTop: 4 }}>매월 25일 · 급여일</div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 26, width: 980 }}>
        {picks.map((p, i) => (
          <NotiCard key={p.career_year} point={p} brand={props.brandColor} company={props.company} index={i} />
        ))}
      </div>

      {/* 시그니처 워터마크 */}
      <div style={{ position: "absolute", bottom: 50, right: 64, fontSize: 26, fontWeight: W.bold, color: hexA("#fff", 0.5) }}>
        급여 알림 · 공기업 딥다이브
      </div>
    </AbsoluteFill>
  );
};

const NotiCard: React.FC<{ point: CareerPoint; brand: string; company: string; index: number }> = ({
  point,
  brand,
  company,
  index,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const start = index * 16;
  const s = spring({ frame: frame - start, fps, config: { damping: 200 }, durationInFrames: 16 });
  const net = point.monthly_net_10k;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 26,
        padding: "26px 32px",
        borderRadius: 28,
        background: "rgba(255,255,255,0.93)",
        boxShadow: "0 24px 60px rgba(0,0,0,0.5)",
        transform: `translateY(${(1 - s) * 40}px) scale(${0.96 + s * 0.04})`,
        opacity: s,
        backdropFilter: "blur(20px)",
      }}
    >
      {/* 앱 아이콘 */}
      <div
        style={{
          width: 88,
          height: 88,
          borderRadius: 22,
          background: `linear-gradient(145deg, ${brand}, ${hexA(brand, 0.7)})`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#fff",
          fontSize: 46,
          fontWeight: W.black,
          flexShrink: 0,
        }}
      >
        ₩
      </div>

      <div style={{ flex: 1, color: "#111" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontSize: 28, fontWeight: W.bold, color: "#6b7280" }}>급여통장</div>
          <div style={{ fontSize: 24, color: "#9ca3af" }}>지금</div>
        </div>
        <div style={{ fontSize: 30, fontWeight: W.semibold, color: "#374151", marginTop: 6 }}>
          입금 <span style={{ color: brand, fontWeight: W.extrabold }}>{won(net)}원</span>
        </div>
        <div style={{ fontSize: 26, color: "#9ca3af", marginTop: 6 }}>
          {company} · {point.grade} {point.career_year}년차 · 월 실수령
        </div>
      </div>
    </div>
  );
};
