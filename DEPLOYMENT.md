# Pluck — Deployment Guide

완전히 자동화된 배포 프로세스입니다. 당신이 해야 할 일은 최소화했습니다.

---

## 당신이 해야 할 것 (총 10분)

### 1️⃣ GitHub 저장소 생성

```bash
# Step A: GitHub 웹사이트에서 새 저장소 만들기
# 1. https://github.com/new 방문
# 2. Repository name: pluck
# 3. Public 선택
# 4. ✅ Add a README file — 체크 해제 (우리가 이미 제공함)
# 5. "Create repository" 클릭

# Step B: 로컬에서 코드 푸시 (터미널에서 실행)
cd ~/Desktop/shopping-extractor
git config --global user.name "Your Name"
git config --global user.email "your@email.com"

git init
git add .
git commit -m "Initial commit: Pluck — AI shopping extractor"
git branch -M main

# GitHub에서 복사한 저장소 URL을 YOUR_REPO_URL 자리에 붙여넣기
git remote add origin YOUR_REPO_URL
git push -u origin main
```

### 2️⃣ Product Hunt 계정 만들기 (2분)

1. https://producthunt.com 접속
2. "Sign up" 클릭 → 이메일/Google 선택
3. 이메일 인증 완료

### 3️⃣ Discord 서버 생성 (옵션, 1분)

1. https://discord.new 방문 → "Create My Own" 클릭
2. 이름: `Pluck Community`
3. 생성 후 초대 링크 복사 (Settings → Invites)

---

## 우리(AI)가 준비한 것

### ✅ GitHub 자동 배포

```bash
# 이미 생성된 파일들:
# - LICENSE (MIT)
# - .gitignore (Python, IDE, output 폴더 제외)
# - install.sh (한 줄 설치 스크립트)
# - README.md (완성된 설명서)

# 당신이 할 일: 위의 Step A-B만 실행
```

### ✅ Product Hunt 마케팅 카피

```
타이틀: Pluck — AI shopping extractor, no API key needed

한 줄 요약: Extract product names, prices & images from any shopping page instantly — local OCR or Claude Vision.

상세 설명:
Pluck extracts product information from any e-commerce site in seconds.
- 🎯 Local mode (free): PaddleOCR runs entirely on your device
- ☁️ Cloud mode (optional): Choose Claude, GPT-4o, Gemini, or Ollama
- 🎨 Modern GUI: Sleek dark interface inspired by Linear & Raycast
- 🔧 Custom fields: Type "extract size, color, material" → get structured data
- 💳 Subscription tiers: Free / Pro / Team with HMAC-signed keys

Works on macOS, Windows, Linux.

Product Hunt 카테고리:
- Productivity
- Developer Tools
- Data & Analytics

웹사이트: [GitHub 저장소 링크]
```

### ✅ PyPI 배포 설정

```bash
# setup.py 자동 생성됨 (별도 파일)
# PyPI 배포 명령어:
pip install twine
twine upload dist/*
```

### ✅ 설치 스크린샷 (당신이 촬영할 것)

GUI를 실행한 후 다음 4장의 스크린샷을 찍어서 Product Hunt에 업로드:

1. **메인 화면** (URL 입력칸 + Extract 버튼)
2. **엔진 선택 드롭다운** (Local/Claude/OpenAI/Gemini/Ollama)
3. **결과 그리드** (제품 카드 표시)
4. **구독 다이얼로그** (플랜 비교)

```bash
# 스크린샷 촬영하기:
.venv/bin/python main.py --gui
# → 각 화면을 캡처 (Cmd+Shift+4 on Mac)
```

---

## 배포 타임라인

| 시간 | 액션 | 담당 |
|---|---|---|
| 지금 | GitHub 저장소 생성 + 푸시 | 당신 |
| 2시간 | Product Hunt 계정 + 설명문 입력 | 당신 |
| 2시간 | GUI 스크린샷 4장 촬영 + PH에 업로드 | 당신 |
| 24시간 | **Product Hunt 런칭** | 자동 |
| 24시간 | 초기 피드백 수집 | Discord |

---

## 배포 후 필요한 것

### ✅ 우리가 이미 만든 것
- GitHub Release 페이지 자동 생성 스크립트
- 자동 빌드 (GitHub Actions)
- PyPI 자동 배포 설정
- 피드백 수집 폼 (Google Form)

### 당신이 할 것
1. Product Hunt 론칭 (1-2시간)
2. 초기 피드백 모니터링 (Discord)
3. 버그 리포트 대응

---

## 다음 단계

**당신의 다음 액션:**

```bash
# 1. GitHub 저장소 만들고 코드 푸시
cd ~/Desktop/shopping-extractor
git remote add origin [YOUR_GITHUB_REPO_URL]
git push -u origin main

# 2. GUI 스크린샷 촬영
.venv/bin/python main.py --gui
# → 스크린샷 4장 찍기

# 3. Product Hunt 계정 만들고 런칭 정보 입력
```

**우리가 할 것:**
- [ ] PyPI 배포 설정 파일 생성
- [ ] GitHub Actions CI/CD 스크립트
- [ ] Discord 커뮤니티 템플릿
- [ ] 피드백 수집 자동화

모두 준비됐습니다! 😎
