# Pluck Remotion 렌더러

공기업 연봉 딥다이브 영상/썸네일을 **코드로** 렌더링한다 (React + Remotion).
PIL 기반 카드 생성기를 대체하는 새 디자인 엔진.

```
Python 파이프라인 (데이터/연봉/분석)
   └─ src/generators/remotion_export.py → remotion/public/props.json
        └─ Remotion (React 컴포지션 + Pretendard + 모션)
             └─ MP4 (영상) / PNG (썸네일)
```

## 디자인 시스템
- 컨셉: 프리미엄 금융 다크 (딥네이비 그라디언트 + 네온그린 실수령 + 골드 강조)
- 폰트: **Pretendard** (npm 패키지, `npm run copy-fonts`로 public/fonts에 복사)
- 컴포지션:
  - `Thumbnail` (1280×720, 스틸) — 신입 실수령 → 30년차 후킹
  - `DeepDive` (1920×1080) — 인트로 → 연차 1~30 카드(카운트업 모션) → CTA

## 설치
```bash
cd remotion
npm install          # postinstall에서 폰트 자동 복사 (아래 스크립트 참고)
npm run copy-fonts   # 수동 복사 (Pretendard woff2 → public/fonts)
```

## 데이터 준비 (Python)
```bash
# 파이프라인이 remotion/public/props.json 을 생성
python -c "from src.generators.remotion_export import build_props, write_props; ..."
```
또는 `main.py`가 생성 단계에서 자동으로 props.json을 내보낸다.

## 렌더
```bash
# 스튜디오(실시간 미리보기/디자인 편집)
npm run dev

# 썸네일 PNG
npm run thumbnail        # → out/thumbnail.png

# 전체 영상 MP4
npm run render           # → out/video.mp4
```

### 헤드리스 크로미움이 막힌 환경 (CI/클라우드)
Remotion 기본 크로미움 배포처(remotion.media)가 차단된 경우,
chrome-for-testing 바이너리를 받아 직접 지정한다:
```bash
npx puppeteer browsers install chrome-headless-shell
CHROME=$(find ~/.cache/puppeteer -name chrome-headless-shell -type f | head -1)
npx remotion still Thumbnail out/thumbnail.png --browser-executable="$CHROME"
npx remotion render DeepDive out/video.mp4 --browser-executable="$CHROME"
```

## 확장 (다음 단계)
- 기업규모/근무지/복지/혜택 씬 컴포넌트 추가 (Thumbnail·SalaryScene과 동일 패턴)
- 내레이션 오디오 트랙 합성 (`<Audio src={staticFile('narration.mp3')} />`)
- 자막(SRT) 오버레이
- 대규모 배치: Remotion Lambda (Vercel/AWS) — 기업당 1영상 자동 렌더
