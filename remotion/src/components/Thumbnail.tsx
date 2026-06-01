import { AbsoluteFill } from "remotion";
import { PALETTE, W } from "../theme";
import { DeepDiveProps, won, comma } from "../lib/format";
import { ensureFonts } from "../load-fonts";

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
        background: PALETTE.ink,
        fontFamily: "Pretendard, sans-serif",
        color: PALETTE.white,
        overflow: "hidden",
      }}
    >
      {/* 좌측 브랜드 컬러 세로 막대 (편집자가 Premiere에서 넣은 느낌) */}
      <div style={{
        position: "absolute",
        left: 0, top: 0, bottom: 0,
        width: 10,
        background: brandColor,
      }} />

      {/* 상단 — 기업명 배지 + 시리즈 레이블 */}
      <div style={{
        position: "absolute",
        top: 52, left: 60,
        display: "flex", alignItems: "center", gap: 16,
      }}>
        <div style={{
          padding: "10px 24px",
          border: `2.5px solid ${brandColor}`,
          borderRadius: 5,
          fontSize: 32,
          fontWeight: W.bold,
          color: brandColor,
          letterSpacing: 1,
        }}>
          {company}
        </div>
        <div style={{
          fontSize: 24,
          fontWeight: W.semibold,
          color: PALETTE.gray,
          letterSpacing: 3,
        }}>
          연봉 딥다이브
        </div>
      </div>

      {/* 메인 카피 블록 — 좌정렬 (인간이 만든 비대칭 레이아웃) */}
      <div style={{
        position: "absolute",
        left: 60, top: 148,
      }}>
        {/* 라벨 — 형광펜 하이라이트 */}
        <div style={{
          fontSize: 40,
          fontWeight: W.semibold,
          color: PALETTE.gray,
          marginBottom: 4,
          letterSpacing: 2,
        }}>
          신입 첫 달{" "}
          <span style={{
            background: PALETTE.highlight,
            color: "#111",
            padding: "0 8px 3px",
            borderRadius: 3,
          }}>
            실수령
          </span>
        </div>

        {/* 핵심 숫자 — 글로우 없는 순수한 흰색 */}
        <div style={{
          display: "flex",
          alignItems: "baseline",
          gap: 6,
          lineHeight: 0.9,
        }}>
          <span style={{
            fontSize: 260,
            fontWeight: W.black,
            color: "#ffffff",
            letterSpacing: -10,
          }}>
            {net1}
          </span>
          <span style={{
            fontSize: 80,
            fontWeight: W.extrabold,
            color: "#cccccc",
          }}>
            만원
          </span>
        </div>

        {/* 구분선 */}
        <div style={{
          width: 540,
          height: 2,
          background: "rgba(255,255,255,0.12)",
          margin: "16px 0",
        }} />

        {/* 30년차 라인 */}
        <div style={{
          display: "flex",
          alignItems: "baseline",
          gap: 16,
        }}>
          <span style={{
            fontSize: 40,
            fontWeight: W.semibold,
            color: PALETTE.gray,
          }}>
            30년차 세전
          </span>
          <span style={{
            fontSize: 86,
            fontWeight: W.black,
            color: PALETTE.warmGold,
            letterSpacing: -2,
          }}>
            {grossLast}
          </span>
          <span style={{
            fontSize: 40,
            fontWeight: W.semibold,
            color: PALETTE.gray,
          }}>
            까지
          </span>
        </div>
      </div>

      {/* 우하단 — 빨간 스탬프 (약간 기울어진 것 = 손으로 찍은 느낌) */}
      <div style={{
        position: "absolute",
        right: 62, bottom: 54,
        textAlign: "right",
      }}>
        <div style={{
          display: "inline-block",
          padding: "12px 26px",
          border: `3px solid ${PALETTE.marker}`,
          borderRadius: 5,
          fontSize: 32,
          fontWeight: W.extrabold,
          color: PALETTE.marker,
          letterSpacing: 2,
          transform: "rotate(-2deg)",
        }}>
          호봉표 전격공개
        </div>
        <div style={{
          marginTop: 10,
          fontSize: 20,
          color: "#444",
          letterSpacing: 1,
        }}>
          알리오 공식자료 기준 · {comma(first.annual_gross_10k)}만 → {comma(last.annual_gross_10k)}만
        </div>
      </div>
    </AbsoluteFill>
  );
};
