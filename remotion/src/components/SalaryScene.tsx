import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { PALETTE, W } from "../theme";
import { CareerPoint, manToWon, comma } from "../lib/format";
import { ensureFonts } from "../load-fonts";

/**
 * 보수명세 카드 (레퍼런스 "연봉계산기" 채널 포맷)
 * 흰 카드 + 항목별 명세(월간환산|연간) + 보수총액/실수령/평달실수령 + 공제 패널
 */
export const SalaryScene: React.FC<{
  point: CareerPoint;
  company: string;
  brandColor: string;
  total: number;
}> = ({ point, company, brandColor, total }) => {
  ensureFonts();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 14 });
  const t = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });

  const base = point.base_salary_10k ?? 0;
  const fixed = point.fixed_allow_10k ?? 0;
  const perform = point.perform_allow_10k ?? 0;
  const welfare = point.welfare_10k ?? 0;
  const bonus = point.bonus_10k ?? 0;
  const grossM = point.monthly_gross_10k;
  const grossY = point.annual_gross_10k;
  const netM = point.monthly_net_10k;
  const netY = netM * 12;
  const regularNet = point.monthly_regular_net_10k ?? 0;

  const rows: Array<[string, number]> = [
    ["기본급", base],
    ["고정수당", fixed],
    ["실적수당", perform],
    ["복리후생비", welfare],
    ["성과상여금", bonus],
  ];

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(180deg,#05070d 0%,#0a0e18 100%)",
        fontFamily: "Pretendard, sans-serif",
        color: PALETTE.white,
      }}
    >
      {/* 좌상단 기업명 */}
      <div style={{ position: "absolute", top: 40, left: 56, fontSize: 40, fontWeight: W.extrabold }}>
        {company}
      </div>

      {/* 흰 카드 */}
      <div
        style={{
          position: "absolute",
          left: 70,
          top: 120,
          width: 1320,
          height: 880,
          background: "#ffffff",
          borderRadius: 18,
          boxShadow: `0 0 80px ${PALETTE.netGlow}`,
          color: "#1a1a1a",
          padding: "44px 54px",
          opacity: enter,
          transform: `translateY(${(1 - enter) * 30}px)`,
        }}
      >
        {/* 헤더: 로고자리 + ver / 직급·연차 */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: 12,
                background: brandColor,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#fff",
                fontSize: 30,
                fontWeight: W.black,
              }}
            >
              ₩
            </div>
            <div style={{ fontSize: 40, fontWeight: W.extrabold, color: "#111" }}>{company}</div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 30, fontWeight: W.bold, color: "#888" }}>ver. 2024</div>
            <div style={{ fontSize: 34, fontWeight: W.extrabold, color: "#111", marginTop: 4 }}>
              {point.grade}{" "}
              <span style={{ color: PALETTE.danger }}>{point.career_year}년차</span>
            </div>
          </div>
        </div>

        {/* 컬럼 헤더 */}
        <div style={{ display: "flex", marginTop: 38, paddingBottom: 10, borderBottom: "2px solid #e5e7eb" }}>
          <div style={{ flex: 1 }} />
          <div style={{ width: 320, textAlign: "right", fontSize: 26, fontWeight: W.bold, color: PALETTE.danger }}>
            월간 환산
          </div>
          <div style={{ width: 360, textAlign: "right", fontSize: 26, fontWeight: W.bold, color: brandColor }}>
            연간
          </div>
        </div>

        {/* 항목 행 (파란 박스 그룹) */}
        <div style={{ border: `2px solid ${brandColor}33`, borderRadius: 10, marginTop: 16, padding: "8px 18px" }}>
          {rows.map(([label, valM], i) => {
            const reveal = interpolate(frame, [4 + i * 3, 16 + i * 3], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            return (
              <div
                key={label}
                style={{
                  display: "flex",
                  alignItems: "center",
                  height: 70,
                  opacity: reveal,
                  transform: `translateX(${(1 - reveal) * 20}px)`,
                }}
              >
                <div style={{ flex: 1, fontSize: 32, fontWeight: W.semibold, color: "#374151" }}>{label}</div>
                <div style={{ width: 320, textAlign: "right", fontSize: 34, fontWeight: W.bold, color: "#111" }}>
                  {manToWon(valM)} <span style={{ fontSize: 22, color: "#9ca3af" }}>원</span>
                </div>
                <div style={{ width: 360, textAlign: "right", fontSize: 34, fontWeight: W.bold, color: "#111" }}>
                  {manToWon(valM * 12)} <span style={{ fontSize: 22, color: "#9ca3af" }}>원</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* 보수총액 / 실수령 (빨간 박스) */}
        <div style={{ border: `3px solid ${PALETTE.danger}`, borderRadius: 12, marginTop: 22, padding: "6px 18px" }}>
          <SumRow label="보수총액" monthly={manToWon(grossM)} annual={comma(grossY * 10000)} big color={PALETTE.danger} />
          <SumRow label="실수령" monthly={manToWon(netM)} annual={manToWon(netY)} color="#111" />
        </div>

        {/* 평달 실수령액 (핑크 강조) */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            marginTop: 18,
            padding: "16px 22px",
            borderRadius: 12,
            background: "#fde7ef",
          }}
        >
          <div style={{ flex: 1, fontSize: 32, fontWeight: W.extrabold, color: "#be1558" }}>평달 실수령액</div>
          <div style={{ fontSize: 46, fontWeight: W.black, color: brandColor }}>
            {manToWon(regularNet * t)} <span style={{ fontSize: 26 }}>원</span>
          </div>
        </div>
      </div>

      {/* 우측 공제 패널 */}
      <div style={{ position: "absolute", right: 56, top: 150, width: 420, opacity: enter }}>
        <Panel title="연봉 계산 기준">
          <li>보수규정 (24.1월)</li>
          <li>대졸 · 무경력 · 호봉표</li>
        </Panel>
        <div style={{ height: 28 }} />
        <Panel title="실수령 공제 항목">
          <li>국민연금 4.5%</li>
          <li>건강보험 3.545%</li>
          <li>장기요양 0.459%</li>
          <li>고용보험 0.9%</li>
          <li>근로소득세 · 지방소득세</li>
        </Panel>
        <div style={{ marginTop: 28, fontSize: 22, color: PALETTE.dim, lineHeight: 1.5 }}>
          ※ 평달 실수령 = 성과급 등 비정기 항목을 제외한, 매달 정기적으로 받는 실수령액
        </div>
      </div>

      {/* 하단 진행바 */}
      <div style={{ position: "absolute", bottom: 0, left: 0, width: "100%", height: 8, background: "rgba(255,255,255,0.08)" }}>
        <div style={{ width: `${(point.career_year / total) * 100}%`, height: "100%", background: brandColor }} />
      </div>
    </AbsoluteFill>
  );
};

const SumRow: React.FC<{ label: string; monthly: string; annual: string; big?: boolean; color: string }> = ({
  label,
  monthly,
  annual,
  big,
  color,
}) => (
  <div style={{ display: "flex", alignItems: "center", height: big ? 84 : 72 }}>
    <div style={{ flex: 1, fontSize: 36, fontWeight: W.extrabold, color: "#111" }}>{label}</div>
    <div style={{ width: 320, textAlign: "right", fontSize: big ? 38 : 34, fontWeight: W.bold, color }}>
      {monthly} <span style={{ fontSize: 22, color: "#9ca3af" }}>원</span>
    </div>
    <div style={{ width: 360, textAlign: "right", fontSize: big ? 48 : 34, fontWeight: W.black, color }}>
      {annual} <span style={{ fontSize: 22, color: "#9ca3af" }}>원</span>
    </div>
  </div>
);

const Panel: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div>
    <div style={{ fontSize: 28, fontWeight: W.extrabold, color: PALETTE.white, marginBottom: 12 }}>{title}</div>
    <ul
      style={{
        margin: 0,
        paddingLeft: 0,
        listStyle: "none",
        display: "flex",
        flexDirection: "column",
        gap: 10,
        fontSize: 26,
        fontWeight: W.semibold,
        color: PALETTE.gray,
      }}
    >
      {children}
    </ul>
  </div>
);
