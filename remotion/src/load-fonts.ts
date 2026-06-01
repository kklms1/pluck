import { staticFile, delayRender, continueRender } from "remotion";

/**
 * Pretendard 로컬 woff2 로딩.
 * public/fonts/ 에 woff2가 복사되어 있어야 한다 (npm run copy-fonts).
 * 렌더 시 폰트 적용 전 프레임이 캡처되지 않도록 delayRender로 보장.
 */
const WEIGHTS: Array<[number, string]> = [
  [400, "Pretendard-Regular.woff2"],
  [500, "Pretendard-Medium.woff2"],
  [600, "Pretendard-SemiBold.woff2"],
  [700, "Pretendard-Bold.woff2"],
  [800, "Pretendard-ExtraBold.woff2"],
  [900, "Pretendard-Black.woff2"],
];

let loaded = false;

export function ensureFonts() {
  if (loaded || typeof document === "undefined") return;
  loaded = true;
  const handle = delayRender("loading-pretendard");
  Promise.all(
    WEIGHTS.map(async ([weight, file]) => {
      try {
        const face = new FontFace(
          "Pretendard",
          `url(${staticFile("fonts/" + file)}) format('woff2')`,
          { weight: String(weight) }
        );
        await face.load();
        (document.fonts as FontFaceSet).add(face);
      } catch (e) {
        // 폰트 누락 시에도 렌더는 진행 (fallback sans-serif)
      }
    })
  ).then(() => continueRender(handle));
}
