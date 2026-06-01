import { Composition, Series, AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Thumbnail } from "./components/Thumbnail";
import { SalaryScene } from "./components/SalaryScene";
import { BankAlert } from "./components/BankAlert";
import { PALETTE, W, bgGradient, hexA } from "./theme";
import { DeepDiveProps, won } from "./lib/format";
import { ensureFonts } from "./load-fonts";
import sample from "../public/props.json";

const FPS = 30;
const HOOK_F = 90;
const CARD_F = 75;
const CTA_F = 150;

const HookScene: React.FC<DeepDiveProps> = (props) => {
  ensureFonts();
  const frame = useCurrentFrame();
  const first = props.career[0];
  const last = props.career[props.career.length - 1];
  const up = interpolate(frame, [0, 20], [40, 0], { extrapolateRight: "clamp" });
  const op = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: bgGradient(props.brandColor), fontFamily: "Pretendard", color: PALETTE.white, justifyContent: "center", alignItems: "center" }}>
      <div style={{ transform: `translateY(${up}px)`, opacity: op, textAlign: "center" }}>
        <div style={{ fontSize: 48, fontWeight: W.bold, color: props.brandColor }}>{props.company}</div>
        <div style={{ fontSize: 64, fontWeight: W.semibold, color: PALETTE.gray, marginTop: 30 }}>신입 첫 달 실수령</div>
        <div style={{ fontSize: 300, fontWeight: W.black, color: PALETTE.net, lineHeight: 1, textShadow: `0 0 80px ${PALETTE.netGlow}` }}>
          {Math.round(first.monthly_net_10k)}<span style={{ fontSize: 100 }}>만원</span>
        </div>
        <div style={{ fontSize: 56, fontWeight: W.bold, color: PALETTE.gray, marginTop: 20 }}>
          30년차엔 <span style={{ color: PALETTE.gold, fontWeight: W.black }}>{won(last.annual_gross_10k)}</span>까지
        </div>
      </div>
    </AbsoluteFill>
  );
};

const CtaScene: React.FC<DeepDiveProps> = (props) => {
  ensureFonts();
  const frame = useCurrentFrame();
  const op = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: bgGradient(props.brandColor), fontFamily: "Pretendard", color: PALETTE.white, justifyContent: "center", alignItems: "center", opacity: op }}>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 88, fontWeight: W.black }}>{props.company} 합격의 모든 것</div>
        <div style={{ marginTop: 50, fontSize: 52, fontWeight: W.bold, color: PALETTE.net }}>자기소개서 기출 분석 PDF</div>
        <div style={{ marginTop: 16, fontSize: 52, fontWeight: W.bold, color: PALETTE.net }}>NCS + 직무 기출변형 문제집</div>
        <div style={{ marginTop: 60, fontSize: 40, color: PALETTE.gray }}>▶ 설명란 링크 · 구독하면 다음 기업 딥다이브 알림</div>
      </div>
    </AbsoluteFill>
  );
};

// 정지 미리보기용 — 대표 연차(6년차 또는 중앙)를 settled 상태로 표시
const SalaryCardStill: React.FC<DeepDiveProps> = (props) => {
  const career = props.career || [];
  const pick = career.find((p) => p.career_year === 6) || career[Math.floor(career.length / 2)] || career[0];
  return <SalaryScene point={pick} company={props.company} brandColor={props.brandColor} total={career.length} />;
};

const DeepDive: React.FC<DeepDiveProps> = (props) => {
  const career = props.career || [];
  return (
    <Series>
      <Series.Sequence durationInFrames={HOOK_F}>
        <HookScene {...props} />
      </Series.Sequence>
      {career.map((p) => (
        <Series.Sequence key={p.career_year} durationInFrames={p.career_year % 5 === 0 ? CARD_F + 15 : CARD_F}>
          <SalaryScene point={p} company={props.company} brandColor={props.brandColor} total={career.length} />
        </Series.Sequence>
      ))}
      <Series.Sequence durationInFrames={CTA_F}>
        <CtaScene {...props} />
      </Series.Sequence>
    </Series>
  );
};

export const RemotionRoot: React.FC = () => {
  const data = sample as DeepDiveProps;
  const total =
    HOOK_F + CTA_F + data.career.reduce((a, p) => a + (p.career_year % 5 === 0 ? CARD_F + 15 : CARD_F), 0);
  return (
    <>
      <Composition
        id="Thumbnail"
        component={Thumbnail}
        durationInFrames={1}
        fps={FPS}
        width={1280}
        height={720}
        defaultProps={data}
      />
      <Composition
        id="BankAlert"
        component={BankAlert}
        durationInFrames={120}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={data}
      />
      <Composition
        id="SalaryCard"
        component={SalaryCardStill}
        durationInFrames={60}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={data}
      />
      <Composition
        id="DeepDive"
        component={DeepDive}
        durationInFrames={total}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={data}
        calculateMetadata={({ props }) => {
          const c = (props as DeepDiveProps).career || [];
          const t = HOOK_F + CTA_F + c.reduce((a, p) => a + (p.career_year % 5 === 0 ? CARD_F + 15 : CARD_F), 0);
          return { durationInFrames: Math.max(t, 1) };
        }}
      />
    </>
  );
};
