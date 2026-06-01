import { Audio, Composition, Series, AbsoluteFill, interpolate, staticFile, useCurrentFrame } from "remotion";
import { Thumbnail } from "./components/Thumbnail";
import { SalaryScene } from "./components/SalaryScene";
import { BankAlert } from "./components/BankAlert";
import { CompanyProfileScene } from "./components/CompanyProfileScene";
import { LocationScene } from "./components/LocationScene";
import { WelfareScene } from "./components/WelfareScene";
import { PALETTE, W, hexA } from "./theme";
import { DeepDiveProps, won } from "./lib/format";
import { ensureFonts } from "./load-fonts";
import sample from "../public/props.json";

const FPS = 30;
const HOOK_F    = 90;
const PROFILE_F = 90;   // 기업규모 + 블라인드
const LOCATION_F = 75;  // 본사위치 + 순환근무
const CARD_F    = 75;
const WELFARE_F = 90;   // 복리후생 그리드
const CTA_F     = 150;

// 총 프레임 계산
function calcTotal(career: DeepDiveProps["career"]) {
  return (
    HOOK_F + PROFILE_F + LOCATION_F + WELFARE_F + CTA_F +
    career.reduce((a, p) => a + (p.career_year % 5 === 0 ? CARD_F + 15 : CARD_F), 0)
  );
}

const HookScene: React.FC<DeepDiveProps> = (props) => {
  ensureFonts();
  const frame = useCurrentFrame();
  const first = props.career[0];
  const last = props.career[props.career.length - 1];

  const op = interpolate(frame, [0, 14], [0, 1], { extrapolateRight: "clamp" });
  const up = interpolate(frame, [0, 14], [28, 0], { extrapolateRight: "clamp" });

  // 숫자 카운트업 — 0 → 실수령 (25프레임에 완성)
  const count = Math.round(
    interpolate(frame, [8, 32], [0, first.monthly_net_10k], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
    })
  );

  return (
    <AbsoluteFill style={{
      background: PALETTE.ink,
      fontFamily: "Pretendard",
      color: PALETTE.white,
      justifyContent: "center",
      alignItems: "center",
    }}>
      {/* 브랜드 세로막대 */}
      <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 10, background: props.brandColor }} />

      <div style={{ transform: `translateY(${up}px)`, opacity: op, textAlign: "center" }}>
        {/* 기업명 */}
        <div style={{
          fontSize: 46,
          fontWeight: W.bold,
          color: props.brandColor,
          letterSpacing: 4,
          marginBottom: 12,
        }}>
          {props.company}
        </div>

        {/* 라벨 — 형광펜 */}
        <div style={{ fontSize: 56, fontWeight: W.semibold, color: PALETTE.gray, marginBottom: 10 }}>
          신입 첫 달{" "}
          <span style={{
            background: PALETTE.highlight,
            color: "#111",
            padding: "0 10px 4px",
            borderRadius: 3,
          }}>
            실수령
          </span>
        </div>

        {/* 핵심 숫자 */}
        <div style={{
          fontSize: 300,
          fontWeight: W.black,
          color: "#ffffff",
          lineHeight: 0.9,
          letterSpacing: -10,
        }}>
          {count}<span style={{ fontSize: 100, color: "#cccccc" }}>만원</span>
        </div>

        {/* 30년차 */}
        <div style={{ fontSize: 56, fontWeight: W.bold, color: PALETTE.gray, marginTop: 24 }}>
          30년차엔{" "}
          <span style={{ color: PALETTE.warmGold, fontWeight: W.black }}>
            {won(last.annual_gross_10k)}
          </span>
          까지
        </div>
      </div>
    </AbsoluteFill>
  );
};

const CtaScene: React.FC<DeepDiveProps> = (props) => {
  ensureFonts();
  const frame = useCurrentFrame();
  const op = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{
      background: PALETTE.ink,
      fontFamily: "Pretendard",
      color: PALETTE.white,
      justifyContent: "center",
      alignItems: "center",
      opacity: op,
    }}>
      {/* 브랜드 막대 */}
      <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 10, background: props.brandColor }} />

      <div style={{ textAlign: "left", paddingLeft: 120 }}>
        {/* 타이틀 */}
        <div style={{ fontSize: 80, fontWeight: W.black, color: PALETTE.white, lineHeight: 1.1 }}>
          {props.company}
          <br />
          <span style={{
            background: PALETTE.highlight,
            color: "#111",
            padding: "2px 14px 6px",
            borderRadius: 4,
          }}>
            합격의 모든 것
          </span>
        </div>

        {/* 구분선 */}
        <div style={{ width: 600, height: 3, background: "rgba(255,255,255,0.12)", margin: "36px 0" }} />

        {/* 상품 목록 */}
        {["자기소개서 기출 분석 PDF", "NCS + 직무 기출변형 문제집"].map((item) => (
          <div key={item} style={{
            display: "flex", alignItems: "center", gap: 18,
            fontSize: 48, fontWeight: W.bold, color: PALETTE.white, marginBottom: 16,
          }}>
            <div style={{
              width: 36, height: 36,
              borderRadius: 4,
              background: props.brandColor,
              flexShrink: 0,
            }} />
            {item}
          </div>
        ))}

        {/* 행동 유도 */}
        <div style={{ marginTop: 40, fontSize: 34, color: PALETTE.gray, letterSpacing: 1 }}>
          ▶ 설명란 링크{" "}
          <span style={{ color: PALETTE.white }}>·</span>{" "}
          구독하면 다음 기업 딥다이브 알림
        </div>
      </div>
    </AbsoluteFill>
  );
};

// 정지 미리보기용 — 대표 연차(6년차 또는 중앙) settled 상태로 표시
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

      <Series.Sequence durationInFrames={PROFILE_F}>
        <CompanyProfileScene {...props} />
      </Series.Sequence>

      <Series.Sequence durationInFrames={LOCATION_F}>
        <LocationScene {...props} />
      </Series.Sequence>

      {career.map((p) => (
        <Series.Sequence key={p.career_year} durationInFrames={p.career_year % 5 === 0 ? CARD_F + 15 : CARD_F}>
          <SalaryScene point={p} company={props.company} brandColor={props.brandColor} total={career.length} />
        </Series.Sequence>
      ))}

      <Series.Sequence durationInFrames={WELFARE_F}>
        <WelfareScene {...props} />
      </Series.Sequence>

      <Series.Sequence durationInFrames={CTA_F}>
        <CtaScene {...props} />
      </Series.Sequence>
    </Series>
  );
};

export const RemotionRoot: React.FC = () => {
  const data = sample as DeepDiveProps;
  const total = calcTotal(data.career);
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
          const t = calcTotal(c);
          return { durationInFrames: Math.max(t, 1) };
        }}
      />
    </>
  );
};
