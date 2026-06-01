import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { PALETTE, W } from "../theme";
import { DeepDiveProps, CareerPoint, comma } from "../lib/format";
import { ensureFonts } from "../load-fonts";

/**
 * 시그니처 씬 — "성장 급여 기록"
 * 1년차 / 15년차 / 30년차 세 시점을 플랫 카드로 병렬 비교.
 * 글라스모피즘 없음 — 단색 다크 배경 + 플랫 카드.
 */

export const BankAlert: React.FC<DeepDiveProps> = (props) => {
  ensureFonts();
  const career = props.career || [];
  const pick = (y: number) =>
    career.find((p) => p.career_year === y) || career[Math.min(y - 1, career.length - 1)];
  const picks = [pick(1), pick(15), pick(30)].filter(Boolean) as CareerPoint[];

  return (
    <AbsoluteFill style={{
      background: PALETTE.ink,
      fontFamily: "Pretendard, sans-serif",
    }}>
      {/* 브랜드 세로막대 */}
      <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 10, background: props.brandColor }} />

      {/* 헤더 */}
      <div style={{
        position: "absolute", top: 60, left: 70, right: 70,
        display: "flex", justifyContent: "space-between", alignItems: "center",
      }}>
        <div style={{ fontSize: 38, fontWeight: W.bold, color: props.brandColor, letterSpacing: 3 }}>
          {props.company} — 급여 성장 기록
        </div>
        <div style={{ fontSize: 26, color: PALETTE.gray }}>매월 25일 · 급여일</div>
      </div>

      {/* 카드 행 */}
      <div style={{
        position: "absolute",
        left: 70, right: 70, top: 148, bottom: 70,
        display: "flex",
        gap: 28,
      }}>
        {picks.map((p, i) => (
          <PayCard key={p.career_year} point={p} brand={props.brandColor} company={props.company} index={i} />
        ))}
      </div>

      {/* 워터마크 */}
      <div style={{
        position: "absolute", bottom: 26, right: 70,
        fontSize: 22, color: "#333", letterSpacing: 1,
      }}>
        알리오 보수규정 기준 · 공기업 딥다이브
      </div>
    </AbsoluteFill>
  );
};

const PayCard: React.FC<{ point: CareerPoint; brand: string; company: string; index: number }> = ({
  point, brand, company, index,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const start = index * 18;
  const s = spring({ frame: frame - start, fps, config: { damping: 200 }, durationInFrames: 18 });
  const net = point.monthly_net_10k;
  const isFirst = index === 0;
  const isLast = index === 2;

  return (
    <div style={{
      flex: 1,
      background: "#1a1a1a",
      borderRadius: 14,
      padding: "36px 32px",
      borderTop: `5px solid ${isFirst ? "#444" : isLast ? PALETTE.warmGold : brand}`,
      transform: `translateY(${(1 - s) * 40}px)`,
      opacity: s,
      display: "flex",
      flexDirection: "column",
    }}>
      {/* 연차 배지 */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
        <div style={{
          padding: "6px 16px",
          borderRadius: 5,
          background: isLast ? PALETTE.warmGold : isFirst ? "#333" : brand,
          fontSize: 24,
          fontWeight: W.bold,
          color: isLast ? "#111" : "#fff",
        }}>
          {point.career_year}년차
        </div>
        <div style={{ fontSize: 24, color: PALETTE.gray }}>{point.grade}</div>
      </div>

      {/* 월 실수령 */}
      <div style={{ marginBottom: 6 }}>
        <div style={{ fontSize: 22, color: PALETTE.gray, marginBottom: 4 }}>월 실수령</div>
        <div style={{ fontSize: 56, fontWeight: W.black, color: PALETTE.white, letterSpacing: -2, lineHeight: 1 }}>
          {Math.round(net)}
          <span style={{ fontSize: 28, fontWeight: W.semibold, color: PALETTE.gray }}> 만원</span>
        </div>
      </div>

      {/* 구분선 */}
      <div style={{ height: 1, background: "#2a2a2a", margin: "20px 0" }} />

      {/* 세부 명세 */}
      <MiniRow label="월 세전" value={`${Math.round(point.monthly_gross_10k)}만`} />
      <MiniRow label="세전 연봉" value={`${Math.round(point.annual_gross_10k).toLocaleString()}만`} accent />
      {(point.monthly_regular_net_10k || 0) > 0 && (
        <MiniRow label="평달 실수령" value={`${Math.round(point.monthly_regular_net_10k!)}만`} />
      )}

      {/* 입금 완료 바 */}
      <div style={{
        marginTop: "auto",
        paddingTop: 20,
        display: "flex",
        alignItems: "center",
        gap: 12,
        fontSize: 22,
        color: "#444",
      }}>
        <div style={{
          width: 8, height: 8, borderRadius: "50%",
          background: isLast ? PALETTE.warmGold : brand,
          flexShrink: 0,
        }} />
        {company} 급여통장 입금 완료
      </div>
    </div>
  );
};

const MiniRow: React.FC<{ label: string; value: string; accent?: boolean }> = ({ label, value, accent }) => (
  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 26, marginBottom: 10 }}>
    <span style={{ color: PALETTE.gray }}>{label}</span>
    <span style={{ fontWeight: W.bold, color: accent ? PALETTE.warmGold : PALETTE.white }}>{value}</span>
  </div>
);
